
def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    :see http://stackoverflow.com/a/312464
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]
