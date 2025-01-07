import pytest
from typing import LiteralString
from transaction_processor.qif_parser import QIFParser
from collections import OrderedDict


@pytest.fixture
def expected_qif_content():
    """
    Fixture to provide sample QIF file content for tests.
    """
    return """!Account
NAssets:Checking Accounts:checking-personal
TBank
^
!Type:Bank
C
D10/11/2023
NN/A
PPCS SVC    1749426         WEB ID: 0000450304
T-123.45
LExpenses:Utilities:Mobile Phone
^
C
D10/13/2023
NN/A
PTransfer   12BK4B1         WEB ID: 9000142693
T-100.00
LAssets:Savings Accounts:savings
^
C
D10/13/2023
NN/A
PEDI PYMNTS                 PPD ID: 3464716239
T1234.56
LIncome:Salary
^
"""


@pytest.fixture
def account_config():
    return {
        'full-account-name': 'Assets:Checking Accounts:checking-personal',
        'account-type': 'Bank',
        'colspec': {'date': 0, 'name': 1, 'amount': 2},
    }


@pytest.fixture
def sample_bank_data():
    return """
!Account
NAssets:Checking Accounts:checking-personal
TBank
^
!Type:Bank
C
D12/31/21
NN/A
T-100.00
PTest Payee
LExpenses:Misc
^
"""


@pytest.fixture
def sample_csv_data():
    return [['01/01/2023', 'Sample Payee 1', '100.00'], ['02/01/2023', 'Sample Payee 2', '-50.00']]


@pytest.fixture
def sample_ccard_data():
    return """
!Account
NLiabilities:Credit Cards:creditcard-personal
TCCard
^
!Type:CCard
C
D11/17/2023
NN/A
PMy Clothing Store
T123.45
LExpenses:Shopping:Clothing
^
C
D12/27/2023
NN/A
PMy Grocery Store
T123.45
LExpenses:Food & Dining:Groceries
^
"""


def test_init_from_csv(sample_csv_data, account_config):
    parser = QIFParser()
    parser.init_from_csv(sample_csv_data, account_config)

    assert parser.account_info['N'] == account_config['full-account-name']
    assert parser.account_info['T'] == account_config['account-type']
    assert parser.transaction_type == account_config['account-type']
    assert len(parser.transactions) == 2

    assert parser.transactions[0]['D'] == '01/01/2023'
    assert parser.transactions[0]['P'] == 'Sample Payee 1'
    assert parser.transactions[0]['T'] == '100.00'

    assert parser.transactions[1]['D'] == '02/01/2023'
    assert parser.transactions[1]['P'] == 'Sample Payee 2'
    assert parser.transactions[1]['T'] == '-50.00'


@pytest.fixture
def bank_txn_parser(tmp_path, sample_bank_data: LiteralString):
    # Create a temporary QIF file for testing
    qif_file = tmp_path / "test.qif"
    qif_file.write_text(sample_bank_data)
    parser = QIFParser()
    parser.init_from_qif(str(qif_file))
    return parser


@pytest.fixture
def ccard_txn_parser(tmp_path, sample_ccard_data: LiteralString):
    # Create a temporary QIF file for testing
    qif_file = tmp_path / "test.qif"
    qif_file.write_text(sample_ccard_data)
    parser = QIFParser()
    parser.init_from_qif(str(qif_file))
    return parser


def test_parse_bank_txn(bank_txn_parser):
    assert bank_txn_parser.transaction_type == "Bank"
    assert bank_txn_parser.account_info is not None
    assert bank_txn_parser.account_info["!Account"] == ""
    assert (
        bank_txn_parser.account_info["N"] == "Assets:Checking Accounts:checking-personal"
    )
    assert bank_txn_parser.account_info["T"] == "Bank"
    assert bank_txn_parser.account_info["^"] == ""
    assert len(bank_txn_parser.transactions) == 1
    transaction = bank_txn_parser.transactions[0]
    assert transaction['C'] == ""
    assert transaction['D'] == "12/31/21"
    assert transaction['N'] == "N/A"
    assert transaction['T'] == "-100.00"
    assert transaction['P'] == "Test Payee"
    assert transaction['L'] == "Expenses:Misc"
    assert transaction["^"] == ""


def test_parse_ccard_txn(ccard_txn_parser):
    assert ccard_txn_parser.transaction_type == "CCard"
    assert ccard_txn_parser.account_info is not None
    assert ccard_txn_parser.account_info["!Account"] == ""
    assert (
        ccard_txn_parser.account_info["N"]
        == "Liabilities:Credit Cards:creditcard-personal"
    )
    assert ccard_txn_parser.account_info["T"] == "CCard"
    assert ccard_txn_parser.account_info["^"] == ""
    assert len(ccard_txn_parser.transactions) == 2
    transaction = ccard_txn_parser.transactions[0]
    assert transaction['C'] == ""
    assert transaction['D'] == "11/17/2023"
    assert transaction['N'] == "N/A"
    assert transaction['P'] == "My Clothing Store"
    assert transaction['T'] == "123.45"
    assert transaction['L'] == "Expenses:Shopping:Clothing"
    assert transaction["^"] == ""
    transaction = ccard_txn_parser.transactions[1]
    assert transaction['C'] == ""
    assert transaction['D'] == "12/27/2023"
    assert transaction['N'] == "N/A"
    assert transaction['P'] == "My Grocery Store"
    assert transaction['T'] == "123.45"
    assert transaction['L'] == "Expenses:Food & Dining:Groceries"
    assert transaction["^"] == ""


def test_write(tmp_path, sample_csv_data, account_config):
    parser = QIFParser()
    parser.init_from_csv(sample_csv_data, account_config)

    output_file = tmp_path / "output.qif"
    parser.write(output_file=output_file)

    with open(output_file, 'r') as f:
        content = f.read()

    assert f'N{account_config["full-account-name"]}' in content
    assert f'T{account_config["account-type"]}' in content
    assert f'!Type:{account_config["account-type"]}' in content

    assert "D01/01/2023" in content
    assert "T100.00" in content
    assert "PSample Payee 1" in content

    assert "D02/01/2023" in content
    assert "T-50.00" in content
    assert "PSample Payee 2" in content


def test_sort_transaction():
    txn = OrderedDict(
        [('P', 'Test Payee'), ('T', '-100.00'), ('D', '12/31/21'), ('L', 'Expenses:Misc')]
    )
    sorted_txn = QIFParser.sort_transaction(txn)
    assert list(sorted_txn.keys()) == ['D', 'P', 'T', 'L']


def test_pretty_format():
    txn = OrderedDict(
        [('P', 'Test Payee'), ('T', '-100.00'), ('D', '12/31/21'), ('L', 'Expenses:Misc')]
    )
    formatted = QIFParser.pretty_format(txn)
    assert "D: 12/31/21" in formatted
    assert "T: -100.00" in formatted
    assert "P: Test Payee" in formatted
    assert "L: Expenses:Misc" in formatted


def test_categorize():
    transaction = OrderedDict([('P', 'Test Payee'), ('T', '-100.00')])
    QIFParser.categorize(transaction, "Expenses:Food")
    assert transaction['L'] == "Expenses:Food"


def test_init_from_qif(tmp_path, expected_qif_content: LiteralString):
    """
    Test that a QIF file is parsed and written back correctly.
    """
    expected_content_path = tmp_path / 'expected_content.qif'
    expected_content_path.write_text(expected_qif_content)

    # Parse the expected QIF file
    parser = QIFParser()
    parser.init_from_qif(str(expected_content_path))

    actual_content_path = tmp_path / 'actual_content.qif'
    parser.write(actual_content_path)

    # Read back the written content
    with open(actual_content_path, 'r') as actual_output:
        actual_written_content = actual_output.read()

    # Assert that the input and output contents are the same
    assert expected_qif_content.strip() == actual_written_content.strip()
