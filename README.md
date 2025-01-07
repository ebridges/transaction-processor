# Transaction Processor

## Usage

```text
usage: process_transactions.py [-h] [-a ACCOUNT_NAME] [-c ACCOUNT_CONFIG] [-l LOOKUP_FILE] [-d DATABASE_FILE] [--verbose] input_csv_file

Process and categorize financial transactions to QIF files.

positional arguments:
  input_csv_file        Path to the input CSV file

options:
  -h, --help            show this help message and exit
  -a, --account-name ACCOUNT_NAME
                        Short name of the account for these transactions.
  -c, --account-config ACCOUNT_CONFIG
                        Path to the account config JSON file
  -l, --lookup-file LOOKUP_FILE
                        Path to the lookup JSON file
  -d, --database-file DATABASE_FILE
                        Path to the GnuCash SQLite DB file
  --verbose
```

An included shell script: `transaction_processor/process-transactions.sh.eg` provides a real-world example of how you might use this.

## Account configuration file

Default location: `etc/account-config.json`

### Fields

- Account name: acts as the key for the config for that account.  Can be anything, but by convention is the last part of the `full-account-name`.
- `full-account-name`: hierarchical path of the account in the GnuCash ledger. This is the account (e.g. your credit or checking account) that you're importing transactions for.
- `colspec`: the definition of what columns the required fields for a transaction are located in the source CSV file.  The key names must be: "date", "name", "amount", "check_number".
- `account-type`: one of "Bank", "CCard" (or any of the [standard type names](https://en.wikipedia.org/wiki/Quicken_Interchange_Format#Header_line) from the QIF definition).

### Example

```json
{
    "my-checking-account": {
        "full-account-name": "Assets:Checking Accounts:my-checking-account",
        "colspec": {
            "date": 1,
            "name": 2,
            "amount": 3,
            "check_number": 6
        },
        "account-type": "Bank"
    }
}
```

## Category:Payee lookup file

Default location: `etc/category-payee-lookup.json`

This file is managed by `category_manager.CategoryManager`, which takes care of either matching a payee to a category (e.g. account) automatically based on these matching patterns or prompting a user to specify what category a payee belongs with.

If the file does not exist, `CategoryManager` will create it with all accounts currently in your GnuCash DB.

### Fields

- Keys in this file correspond to the `full-account-name` for any categories
- Each account can have multiple `payee` matching patterns (either `literal` or `regex`)

### Example

```json
{
    "Assets": [],
    "Assets:Cash": [
        {
            "payee": "ATM WITHDRAWAL",
            "type": "literal"
        }
    ],
    "Assets:Checking Accounts:my-checking-account": [],
    "Expenses:Food & Dining:Groceries": [
        {
            "payee": "^Grocery store #[0-9]+$",
            "type": "regex"
        },
    ],
    ...
}
```

## Running tests

To run the tests in the project execute the following from the root directory of the project:

```sh
$ PYTHONPATH=. pytest
```

## References

- QIF File Format: https://en.wikipedia.org/wiki/Quicken_Interchange_Format
- GNUCash Schema Definition: https://wiki.gnucash.org/wiki/SQL
- GNUCash ER Diagram: https://wiki.gnucash.org/wiki/images/8/86/Gnucash_erd.png
