import argparse
import re
import csv
from os import makedirs
from shutil import copyfile
from json import load
from datetime import datetime
from logging import INFO, DEBUG, info, debug, warning, basicConfig
from qif_parser import QIFParser
from category_manager import CategoryManager
from export_accounts import export_gnucash_accounts


# Constants
QIF_DATE_FORMAT = '%m/%d/%Y'
DATE_FIELD = 'date'
DEFAULT_ACCOUNT_CONFIG = 'etc/account-config.json'
DEFAULT_LOOKUP_FILE = 'etc/category-payee-lookup.json'
DEFAULT_DATABASE_FILE = 'accounting-books.db.gnucash'


def configure_logging(verbose: bool) -> None:
    level = DEBUG if verbose else INFO
    basicConfig(
        format='[%(asctime)s][%(levelname)s] %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        level=level,
    )


def get_output_filename(account_name: str, date_range: dict, ext: str) -> str:
    output_dir = f'{datetime.now().year}/{account_name}'
    makedirs(output_dir, exist_ok=True)
    filename = f"{date_range['start']}--{date_range['end']}-{account_name}.{ext}"
    return f'{output_dir}/{filename}'


def read_transactions_from_csv(file_path: str, date_idx: int) -> tuple:
    with open(file_path) as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header row
        sorted_transactions = sorted(
            reader, key=lambda row: datetime.strptime(row[date_idx], QIF_DATE_FORMAT).date()
        )
        if sorted_transactions:
            start_date = datetime.strptime(sorted_transactions[0][date_idx], QIF_DATE_FORMAT).date()
            end_date = datetime.strptime(sorted_transactions[-1][date_idx], QIF_DATE_FORMAT).date()
            return sorted_transactions, {'start': start_date, 'end': end_date}
        return [], {'start': None, 'end': None}


def get_gnucash_accounts(db_path: str) -> list:
    accounts = export_gnucash_accounts(db_url=f'sqlite:///{db_path}')[1:]
    return [account[1] for account in accounts]


def categorize_transaction(payee: str, lookup: dict) -> str:
    if not payee.strip():
        return None
    for category, patterns in lookup.items():
        if any(match_pattern(entry, payee) for entry in patterns):
            debug(f'Matched payee "{payee}" to category "{category}"')
            return category
    debug(f'No pattern matched for payee: "{payee}"')
    return None


def match_pattern(pattern: dict, payee: str) -> bool:
    if pattern['type'] == 'regex':
        return re.search(pattern['payee'], payee) is not None
    elif pattern['type'] == 'literal':
        return pattern['payee'].lower() in payee.lower()
    return False


def handle_uncategorized(transaction: dict, category_manager: CategoryManager) -> str:
    print('_' * 50)
    print(QIFParser.pretty_format(transaction))
    category = collect_category(category_manager)
    if category == CategoryManager.UNCATEGORIZED_ACCOUNT:
        return category
    payee = QIFParser.payee(transaction)
    pattern, match_type = collect_pattern(payee, category_manager)
    if pattern:
        category_manager.update_lookup(category, pattern, match_type)
    return category


def collect_category(category_manager: CategoryManager) -> str:
    category_session = category_manager.category_prompt()
    while True:
        category = category_session.prompt().strip() or CategoryManager.UNCATEGORIZED_ACCOUNT
        if category in category_manager.categories_list:
            info(f'Confirmed that [{category}] is in the list of valid categories')
            return category
        warning(f'Category {category} not found.')


def collect_pattern(payee: str, category_manager: CategoryManager) -> tuple:
    pattern_session = category_manager.pattern_prompt()
    while True:
        pattern_input = pattern_session.prompt().strip()
        if not pattern_input:
            return None, None
        if pattern_input.startswith('/') and pattern_input.endswith('/'):
            pattern = pattern_input[1:-1]
            if re.search(pattern, payee):
                info(f'Confirmed that regex [{pattern}] matches the given payee {payee}')
                return pattern, 'regex'
        else:
            if pattern_input.lower() in payee.lower():
                info(f'Confirmed that literal [{pattern_input}] matches the given payee {payee}')
                return pattern_input, 'literal'
        warning(f'Pattern "{pattern_input}" does not match the payee "{payee}". Please try again.')


def process_transactions(qif_file: QIFParser, category_manager: CategoryManager) -> None:
    for transaction in qif_file.transactions:
        payee = QIFParser.payee(transaction)
        category = categorize_transaction(
            payee, category_manager.lookup_data
        ) or handle_uncategorized(transaction, category_manager)
        if category:
            QIFParser.categorize(transaction, category)


def format_date(date_string: str) -> str:
    '''
    Convert date from MM/DD/YYYY format to YYYY-MM-DD format.

    Parameters:
    - date_string (str): A date string in MM/DD/YYYY format.

    Returns:
    - str: The date string in YYYY-MM-DD format.
    '''
    # Split the input date string into components
    month, day, year = date_string.split("/")
    # Rearrange and format as YYYY-MM-DD
    formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return formatted_date


def main(
    input_csv_file: str,
    account_name: str,
    account_config_path: str,
    lookup_file: str,
    database_file: str,
) -> None:
    account_config = load(open(account_config_path))[account_name]
    transactions, date_range = read_transactions_from_csv(
        input_csv_file, account_config['colspec']['date']
    )
    csv_backup_file = get_output_filename(account_name, date_range, 'csv')
    copyfile(input_csv_file, csv_backup_file)
    category_list = get_gnucash_accounts(database_file)
    category_manager = CategoryManager(lookup_file, category_list)
    qif_parser = QIFParser()
    qif_parser.init_from_csv(transactions, acct_cfg=account_config)
    process_transactions(qif_parser, category_manager)
    qif_output_file = get_output_filename(account_name, date_range, 'qif')
    qif_parser.write(qif_output_file)
    info(f'Categorized transactions saved to: {qif_output_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Process and categorize financial transactions to QIF files.'
    )
    parser.add_argument('input_csv_file', help='Path to the input CSV file')
    parser.add_argument(
        '-a', '--account-name', help='Short name of the account for these transactions.'
    )
    parser.add_argument(
        '-c',
        '--account-config',
        default=DEFAULT_ACCOUNT_CONFIG,
        help='Path to the account config JSON file',
    )
    parser.add_argument(
        '-l', '--lookup-file', default=DEFAULT_LOOKUP_FILE, help='Path to the lookup JSON file'
    )
    parser.add_argument(
        '-d',
        '--database-file',
        default=DEFAULT_DATABASE_FILE,
        help='Path to the categories GnuCash DB file',
    )
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    configure_logging(args.verbose)
    debug(args)
    main(
        args.input_csv_file,
        args.account_name,
        args.account_config,
        args.lookup_file,
        args.database_file,
    )
