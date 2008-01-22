#!/usr/bin/env python

"""This Python script will determine what flavor of bootstrapper
to fetch for your system, download it, and optionally run it."""

import commands, optparse, os, urllib, re, sets, sys

LISTING_URL = 'http://code.google.com/p/faxien/downloads/list'
FILE_URL = 'http://faxien.googlecode.com/files'

INTERACTIVE = os.isatty(sys.stdin.fileno())

# re to find the filenames
scraper = re.compile(r'_go\(\'detail\?name=(faxien-launcher[^&]*)')

# re to find version num in filenames
verpat = re.compile(r'-((\d+.)+)sh')


# ioctl_GWINSZ and terminal_size are from Chuck Blake's cls.py
# http://pdos.csail.mit.edu/~cblake/cls/cls.py

def ioctl_GWINSZ(fd):                  #### TABULATION FUNCTIONS
    try:                                ### Discover terminal width
        import fcntl, termios, struct
        cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
    except:
        return None
    return cr

def terminal_size():                    ### decide on *some* terminal size
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)  # try open fds
    if not cr:                                                  # ...then ctty
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:                            # env vars or finally defaults
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])         # reverse rows, cols


def get_bootstrappers():
    """Return the list of bootstrappers available for download."""

    page = urllib.urlopen(LISTING_URL).read()

    bootstrappers = list(sets.Set(scraper.findall(page)))
    bootstrappers.sort()
    return bootstrappers


def choose_bootstrapper(bootstrappers):
    """Present a menu for the user to choose a bootstrapper and return
    the bootstrapper chosen."""

    if not INTERACTIVE:
        print >>sys.stderr, 'choose mode in a non-interactive environment'
        sys.exit(1)

    while True:
        print 'Choose a bootstrapper from the list:'
        for i, bootstrapper in enumerate(bootstrappers):
            print ' %d: %s' % (i + 1, bootstrapper)

        ans = raw_input('[%d-%d] ' % (1, len(bootstrappers)))

        if not ans:
            print 'Aborting.'
            sys.exit(1)

        ans = ans.isdigit() and int(ans) or None

        if ans and ans >= 1 and ans <= len(bootstrappers):
            return bootstrappers[ans-1]

        print
        print 'Please enter a number between %d and %d.' % (1, len(bootstrappers))
        print


def determine_bootstrapper(options, bootstrappers):
    """Determine which bootstrapper to use based on the options."""
    if options.choose:
        return choose_bootstrapper(bootstrappers)

    if not options.machine:
        status, output = commands.getstatusoutput('uname -m')
        if status != 0:
            print 'Cannot determine machine type.'
            sys.exit(1)
        options.machine = output

    if not options.kernel:
        status, output = commands.getstatusoutput('uname -s')
        if status != 0:
            print 'Cannot determine kernel name.'
            sys.exit(1)
        options.kernel = output

    options.machine = options.machine.replace(' ', '-')
    options.kernel = options.kernel.replace(' ', '-')

    prefix = 'faxien-launcher-%s-%s' % (options.machine, options.kernel)

    # find potential bootstrappers
    matches = [b for b in bootstrappers if b.startswith(prefix)]

    # search for version numbers
    matches = [(verpat.search(b), b) for b in matches]

    # grab the version numbers, cull filenames with no matches
    matches = [(m.group(1)[:-1], b) for m, b in matches if m]

    # tupleize them for sorting
    matches = [(tuple([int(n) for n in vernum.split('.')]), b) for vernum, b in matches]

    # latest version will be last after sort
    matches.sort()

    if not matches:
        print >>sys.stderr, 'No bootstrapper for %s %s' % (options.machine,
                                                           options.kernel)
        sys.exit(1)

    # return the latest bootstrap file
    return matches[-1][1]


SPINNER = "-\|/"
TERMINAL_SIZE = None

def progress_bar(block_count, block_size, total_bytes):
    """Progress hook for urllib.urlretrieve.
    With an interactive shell, display a progress bar for download progress."""
    if not INTERACTIVE:
        return

    if block_count % 10 != 0:
        return

    count = block_count // 10

    progress_length = TERMINAL_SIZE[0] - 6

    bytes = block_count * block_size

    num_bars = progress_length * (bytes / float(total_bytes))
    num_bars = int(num_bars)

    if num_bars:
        last_bars = progress_length * ((bytes - (block_size * 10)) / float(total_bytes))
        last_bars = int(last_bars)
        new_bars = '=' * (num_bars - last_bars)
    else:
        new_bars = ''

    percent = 100 * (bytes / float(total_bytes))
    percent = ' %3d%%' % round(percent)

    sys.stdout.write('\b\b\b\b\b\b' + new_bars + SPINNER[count % len(SPINNER)] + percent)
    sys.stdout.flush()


def download_bootstrapper(bootstrapper):
    """Fetch the given bootstrap file from the website. Return the file location."""
    global TERMINAL_SIZE
    if INTERACTIVE:
        TERMINAL_SIZE = terminal_size()

    url = '%s/%s' % (FILE_URL, bootstrapper)

    print 'Downloading %s' % url
    sys.stdout.write(SPINNER[0] + '    %')

    bootfile = urllib.urlretrieve(url, bootstrapper, reporthook=progress_bar)[0]

    print
    print 'Done.'

    return bootfile


if __name__ == '__main__':
    usage = """%prog [options] [prefix]

    Without options, this script will download the latest version of
    the faxien bootstrapper for your system and optionally run it.
    Additional options allow you to override the choice or choose
    a specific bootstrapper from a list."""

    parser = optparse.OptionParser(usage=usage)

    help = 'run the bootstrapper after download'
    parser.add_option("-r", "--autorun", dest="autorun", action='store_true', help=help)

    help = 'let me choose my bootstrapper from the current available'
    parser.add_option("-c", "--choose", dest="choose", action='store_true', help=help)

    help = 'the type of computer you are running. By default, the output of "uname -m"'
    parser.add_option("-m", "--machine", dest="machine", help=help)

    help = 'the name of the kernel you are running. By default, the output of "uname -s"'
    parser.add_option("-k", "--kernel", dest="kernel", help=help)

    options, args = parser.parse_args()

    if len(args) > 1:
        parser.error('bad arguments')

    bootstrappers = get_bootstrappers()

    bootstrapper = determine_bootstrapper(options, bootstrappers)

    bootfile = download_bootstrapper(bootstrapper)

    if INTERACTIVE and not options.autorun:
        ans = raw_input('Do you want to run the bootstrapper now? ([y]/n) ')
        if ans.lower() not in ('', 'y'):
            sys.exit()

    if not INTERACTIVE and not options.autorun():
        sys.exit()

    prefix = args and args[0] or None

    if INTERACTIVE and not prefix:
        prefix = raw_input('Enter the install prefix: [/usr/local/erlware] ')

    command = 'sh %s %s' % (bootfile, prefix or '')
    print 'Running:', command
    os.system(command)