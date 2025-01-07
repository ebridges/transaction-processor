from collections import OrderedDict

AcctHeader = '!Account'
AcctName = 'N'
AcctType = 'T'
TxnHeader = '!Type'
RecordBegin = 'C'
TxnDate = 'D'
TxnCheckNumber = 'N'
TxnPayee = 'P'
TxnAmount = 'T'
TxnCategory = 'L'
RecordEnd = '^'


class QIFParser:

    def __init__(self):
        """
        Initialize the QIF parser.
        """
        self.account_info = OrderedDict()
        self.transactions = []
        self.transaction_type = None

    def init_from_qif(self, qif_file):
        """
        Parse the QIF file, capturing headers and transactions.

        Raises:
            ValueError: If the file format is invalid.
        """
        with open(qif_file, 'r') as file:
            current_transaction = OrderedDict()
            for line in file:
                line = line.strip()
                if not line:
                    continue

                if line == AcctHeader:
                    in_account_section = True
                    self.account_info = OrderedDict()
                    self.account_info[line] = ''
                elif line.startswith(TxnHeader):
                    self.transaction_type = line.split(':')[1]
                elif line == RecordEnd:  # end of section or transaction
                    if in_account_section:
                        self.account_info[RecordEnd] = ''
                        in_account_section = False
                    else:
                        current_transaction[RecordEnd] = ''
                        self.transactions.append(current_transaction)
                        current_transaction = OrderedDict()
                else:
                    line_type = line[0]
                    line_data = line[1:].strip()
                    if in_account_section:
                        self.account_info[line_type] = line_data
                    else:
                        current_transaction[line_type] = line_data

    def init_from_csv(self, csv_input, acct_cfg):
        self.account_info[AcctHeader] = ''
        self.account_info[AcctName] = acct_cfg['full-account-name']
        self.account_info[AcctType] = acct_cfg['account-type']
        self.account_info[RecordEnd] = ''
        self.transaction_type = acct_cfg['account-type']

        for t in csv_input:
            txn = OrderedDict()
            txn[RecordBegin] = ''
            txn[TxnDate] = t[acct_cfg['colspec']['date']]
            txn[TxnCheckNumber] = 'N/A'
            txn[TxnPayee] = t[acct_cfg['colspec']['name']]
            txn[TxnAmount] = t[acct_cfg['colspec']['amount']]
            txn[TxnCategory] = ''
            txn[RecordEnd] = ''
            self.transactions.append(txn)

    def write(self, output_file):
        """
        Write the parsed QIF data to given file.

        Args:
            output_file: File to write QIF data to.
        """
        with open(output_file, 'w') as output:
            for key in self.account_info.keys():
                output.write(f'{key}{self.account_info[key]}\n')

            output.write(f'!Type:{self.transaction_type}\n')

            for transaction in self.transactions:
                for key, value in self.sort_transaction(transaction).items():
                    output.write(f'{key}{value}\n')

    @classmethod
    def sort_transaction(cls, txn):
        field_order = [
            RecordBegin,
            TxnDate,
            TxnCheckNumber,
            TxnPayee,
            TxnAmount,
            TxnCategory,
            RecordEnd,
        ]
        return OrderedDict((field, txn[field]) for field in field_order if field in txn)

    @classmethod
    def pretty_format(cls, txn):
        formatted = ''
        for key, val in txn.items():
            if key not in (RecordBegin, TxnCheckNumber, RecordEnd):
                formatted += f'{key}: {val}\n'
        return formatted

    @classmethod
    def payee(cls, transaction):
        return transaction.get(TxnPayee)

    @classmethod
    def account(cls, qif_file):
        qif_file.account_info(AcctName)

    @classmethod
    def txn_date(cls, transaction):
        return transaction.get(TxnDate)

    @classmethod
    def amount(cls, transaction):
        return transaction.get(TxnAmount)

    @classmethod
    def category(cls, transaction):
        return transaction.get(TxnCategory)

    @classmethod
    def categorize(cls, transaction, category):
        """
        Add or update the category (L field) in a transaction.

        Args:
            transaction (OrderedDict): The transaction to modify.
            category (str): The category to add or update.
        """
        transaction[TxnCategory] = category
