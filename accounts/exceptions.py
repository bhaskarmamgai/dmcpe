# https://www.codementor.io/sheena/how-to-write-python-custom-exceptions-du107ufv9
class NegativePostingBalanceException(Exception):
    def __init___(self, d_error_arguments):
        Exception.__init__(self,
                           "Posting balance cant be a negative number - Exception was raised with arguments {0}".format(
                               d_error_arguments))
        self.dErrorArguments = d_error_arguments


class ZeroOrNegativePostingAmountException(Exception):
    def __init___(self, d_error_arguments):
        Exception.__init__(self,
                           "Posting amount cant be zero or a negative number - Exception was raised with arguments {0}".format(
                               d_error_arguments))
        self.dErrorArguments = d_error_arguments


class InvalidDebitCreditTypeException(Exception):
    pass


class PostingsAndWalletBalanceMisMatchException(Exception):
    def __init___(self, d_error_arguments):
        Exception.__init__(self,
                           "Postings and Wallet Balance Mismatch, Please Contact Admin - Exception was raised with "
                           "arguments {0}".format(
                               d_error_arguments))
        self.dErrorArguments = d_error_arguments
