""" This module provided the main subtidy logic.
"""

import collections
import enum
import functools
import sys

from . import ParseError

# Add a little colour
#
yellow = "\x1b[33;1m"
blue = "\x1b[36;1m"
reset = "\x1b[00m"
do_debug = False


# Used to hold an various items with a trailing comment
#
with_comment = collections.namedtuple("with_comment", ('item', 'comment'))


# -----------------------------------------------------------------------------
# Like print, except to std error
#
errput = functools.partial(print, file=sys.stderr)

# -----------------------------------------------------------------------------
#


def warning(text, **kwd):
    """ Outputs yellow text to stderr
    """
    errput(f"{yellow}{text}{reset}", **kwd)


# -----------------------------------------------------------------------------
#
def debug(text, **kwd):
    """ Outputs blue text to stderr iff do_debug is True
    """
    if do_debug is True:
        errput(f"{blue}{text}{reset}", **kwd)


# -----------------------------------------------------------------------------
#
def quote_str(value):
    """ If value is not quoted (with ") and pre-fixes and post-fixes with "
    """
    if not value.startswith('"') and not value.endswith('"'):
        value = '"' + value + '"'
    return value


# -----------------------------------------------------------------------------
#
def generate_row(item, target, widths, prefix, spaces, newlines):
    """ Basically the same logic for formal row and actual rows
        item   - the formal or actutal [element]
        target - the target file - must support write()
        widths - the width of each elemet in item
        prefix - either "pattern" or "       "
        spaces - the gap betweeen element on the frow, e.g. "  "
        newlines - list of ints, defines when line breaks occur.

    """
    putline = functools.partial(print, file=target)
    put = functools.partial(print, end="", file=target)

    put(f"{prefix} {{ ")

    if isinstance(item, with_comment):
        c = item.comment
        item = item.item
    else:
        c = None

    number = len(item)
    for j, name in enumerate(item):
        gap = ""
        while len(name) + len(gap) < widths[j]:
            gap = gap + " "

        put(f"{name}")
        if j < number - 1:
            put(f",{spaces}")

        if j in newlines and j < (number - 1):
            # Form modified prefix.
            p = " " * len(prefix)
            put(f"\n{p}   ")
        else:
            put(gap)

    if c is None:
        putline(f" }}")
    else:
        putline(f" }}  {c}")


# -----------------------------------------------------------------------------
#
def generate_substitution(d, target, indent, spacing, width):
    """ Generates/putput the substitution specified in the dictionary d
    """
    putline = functools.partial(print, file=target)
    put = functools.partial(print, end="", file=target)

    # convert to strings
    #
    i = indent * ' '
    s = spacing * ' '
    p = len("pattern") * ' '

    template = d['template']
    comments = d['comments']
    formal = d['formal']
    actual = d['actual']
    eos_comment = d['eos_comment']

    debug(f"   template: {template}")
    debug(f"   comments: {comments}")
    debug(f"   formal: {formal}")
    debug(f"   actual:")
    for act_item in actual:
        debug(f"      {act_item}")
    debug(f"   eos_comment: {eos_comment}\n")

    widths = []
    if isinstance(formal, with_comment):
        f2 = formal.item
        number = len(f2)
        for name in f2:
            widths.append(len(name))
    else:
        # Must be a simple list
        #
        number = len(formal)
        for name in formal:
            widths.append(len(name))

    for row in actual:
        if isinstance(row, str):
            continue

        if isinstance(row, with_comment):
            row = row.item

        n = len(row)
        if n != number:
            raise ValueError(f"{row} has {n} items, {number} expected")

        for j, value in enumerate(row):
            value = quote_str(value)
            row[j] = value

            w = len(value)
            widths[j] = max(widths[j], w)

    # Now process the widths
    # newlines specify item after which a newline is required
    #
    newlines = []
    total = 10
    for j, w in enumerate(widths):
        total += w + spacing + 1
        if total > width:
            newlines.append(j)
            total = 10

    # - - - - - - - - - - - - - - - - - - -
    # Now start the actual output to target
    #
    if isinstance(template, with_comment):
        c = template.comment
        template = quote_str(template.item)
        putline(f"file {template} {{  {c}")
    else:
        # Must be a simpel str
        template = quote_str(template)
        putline(f"file {template} {{")

    for c in comments:
        if c.startswith(" "):
            c = c.lstrip()
            c = "    " + c
        putline(f"{c}")

    generate_row(formal, target, widths, f"{i}pattern", s, newlines)

    for row in actual:
        if isinstance(row, str):
            # This is a comment or white space
            # Output more or less as is.
            #
            if row.startswith(" "):
                row = row.lstrip()
                row = "            " + row
            putline(f"{row}")
            continue

        generate_row(row, target, widths, f"{i}       ", s, newlines)

    if eos_comment is None:
        putline(f"}}")
    else:
        putline(f"}}  {eos_comment}")


# -----------------------------------------------------------------------------
#
def generate(source, target, indent, spacing, width):
    """ Generate a tidy (as in alligned) subscription file.
        source is a list or tuple of items, each item being either a string
        or a dictionary.
        strings are output as is - use for comments and white space.
        dictionaries represent a an actual substituion.
    """
    if not isinstance(source, (list, tuple)):
        raise TypeError(f"unexpected source, type: {type(source)}, expecting a list or tuple")

    for item in source:
        if isinstance(item, str):
            # Simple - just print
            #
            print(item.strip(), file=target)

        elif isinstance(item, dict):
            generate_substitution(item, target=target, indent=indent, spacing=spacing, width=width)

        else:
            raise TypeError(f"unexpected item {item}, type: {type(item)}")


# -----------------------------------------------------------------------------
# comment here includes blank lines
#
Tokens = enum.Enum("Tokens", ('comment', 'eol_comment',
                              'file', 'pattern', 'name',
                              'open_brace', 'close_brace',
                              'comma', 'value', 'end_of_file'))


# -----------------------------------------------------------------------------
#
def get_token(source):
    """ Generator function to tokenise source
        Return a tuple (token type, literal if appliable or empty string, line number, col nunmer )
    """
    lines = source.read().splitlines()
    lineno = 0
    col = 0
    for line in lines:
        lineno += 1
        col = 0
        temp = line.rstrip()
        size = len(temp) + 1
        temp = temp.lstrip()

        if len(temp) == 0 or temp[0] == '#':
            yield (Tokens.comment, line.rstrip(), lineno, col)
            continue

        while len(temp) > 0:
            col = size - len(temp)

            if temp.startswith('#'):
                yield (Tokens.eol_comment, temp.rstrip(), lineno, col)
                temp = ""
                continue

            elif temp.startswith('file'):
                yield (Tokens.file, '', lineno, col)
                temp = temp[4:].lstrip()
                continue

            if temp.startswith('pattern'):
                yield (Tokens.pattern, '', lineno, col)
                temp = temp[7:].lstrip()
                continue

            if temp.startswith('{'):
                yield (Tokens.open_brace, '', lineno, col)
                temp = temp[1:].lstrip()
                continue

            if temp.startswith('}'):
                yield (Tokens.close_brace, '', lineno, col)
                temp = temp[1:].lstrip()
                continue

            if temp.startswith(','):
                yield (Tokens.comma, '', lineno, col)
                temp = temp[1:].lstrip()
                continue

            # must be a name/value
            #
            if temp.startswith('"'):
                # Is a quoted value - find end quote
                # TODO - worry about e.g. "ABC\"DEF"
                #
                q = temp.find('"', 1)
                if q < 0:
                    raise ParseError(f"{source.name}:{lineno}:{col} value missing trailing \"")
                q += 1    # include the quote character
                yield (Tokens.value, temp[:q], lineno, col)
                temp = temp[q:].lstrip()
                continue

            # must be a name or unquoted value
            #
            a1 = temp.find(',')
            if a1 < 0:
                a1 = len(temp)

            a2 = temp.find('{')
            if a2 < 0:
                a2 = len(temp)

            a3 = temp.find('}')
            if a3 < 0:
                a3 = len(temp)

            a4 = temp.find(' ')
            if a4 < 0:
                a4 = len(temp)

            a = min(a1, a2, a3, a4)
            text = temp[:a].rstrip()

            token = Tokens.name
            for c in text:
                if not c.isalnum() and c not in "_+-:":
                    # Yep: '+', '-' and ':' seem to be allowed in formal names
                    token = Tokens.value
                    break

            yield (token, text, lineno, col)
            temp = temp[a:].lstrip()

        # end temp
    # end lines

    # We return an explicit end of file token
    #
    yield (Tokens.end_of_file, '', lineno, col)


# -----------------------------------------------------------------------------
#
def process_source(source):
    """ Parse source substitution file
    """

    # Need better state names
    #
    States = enum.Enum("States", ('seek_file', 'start1', 'start2', 'seek_pattern',
                                  'start_formal', 'seek_name', 'post_name',
                                  'start_actual_first', 'start_actual_next',
                                  'seek_value', 'post_value'))

    result = []
    state = States.seek_file

    template = None
    comments = None
    formal = None
    actual = None
    actual_row = None
    eos_comment = None

    for token, literal, lineno, col in get_token(source):

        st = (state, token)

        # Now examine the state-token combination
        # The 3.10  match case ... case ... syntax would be nice here.
        #
        if st == (States.seek_file, Tokens.comment):
            result.append(literal)

        elif st == (States.seek_file, Tokens.end_of_file):
            # This is not unexpected.
            break

        elif st == (States.seek_file, Tokens.file):
            comments = []
            formal = []
            actual = []
            state = States.start1

        elif st == (States.seek_file, Tokens.eol_comment):
            last = len(result) - 1
            last_item = result[last]
            last_item['eos_comment'] = literal

        elif st == (States.start1, Tokens.value):
            template = literal
            state = States.start2

        elif st == (States.start2, Tokens.open_brace):
            state = States.seek_pattern

        elif st == (States.seek_pattern, Tokens.eol_comment):
            template = with_comment(template, literal)

        elif st == (States.seek_pattern, Tokens.comment):
            comments.append(literal)

        elif st == (States.seek_pattern, Tokens.pattern):
            state = States.start_formal

        elif st == (States.start_formal, Tokens.open_brace):
            state = States.seek_name

        elif st == (States.seek_name, Tokens.name):
            formal.append(literal)
            state = States.post_name

        elif st == (States.seek_name, Tokens.comma):
            last = len(formal) - 1
            last_name = formal[last]
            msg = f"extra comma following macro name {last_name} removed"
            warning(f"{source.name}:{lineno}:{col} {msg}")
            state = States.seek_name

        elif st == (States.seek_name, Tokens.close_brace):
            last = len(formal) - 1
            last_name = formal[last]
            msg = f"extra comma following macro name {last_name} removed"
            warning(f"{source.name}:{lineno}:{col} {msg}")
            state = States.start_actual_first

        elif st == (States.post_name, Tokens.name):
            last = len(formal) - 1
            last_name = formal[last]
            msg = f"missing comma between macro names {last_name} and {literal}"
            warning(f"{source.name}:{lineno}:{col} {msg}")
            formal.append(literal)
            state = States.post_name

        elif st == (States.post_name, Tokens.comma):
            state = States.seek_name

        elif st == (States.post_name, Tokens.close_brace):
            state = States.start_actual_first

        elif st == (States.start_actual_first, Tokens.eol_comment):
            formal = with_comment(formal, literal)

        elif st == (States.start_actual_next, Tokens.eol_comment):
            last = len(actual) - 1
            last_row = actual[last]
            last_row = with_comment(last_row, literal)
            actual[last] = last_row

        elif st == (States.start_actual_first, Tokens.comment):
            actual.append(literal)

        elif st == (States.start_actual_next, Tokens.comment):
            actual.append(literal)

        elif st == (States.start_actual_first, Tokens.open_brace) or \
                st == (States.start_actual_next, Tokens.open_brace):
            actual_row = []
            state = States.seek_value

        elif st == (States.seek_value, Tokens.value) or \
                st == (States.seek_value, Tokens.name):
            actual_row.append(literal)
            state = States.post_value

        elif st == (States.seek_value, Tokens.comma):
            last = len(actual_row) - 1
            last_value = actual_row[last]
            msg = f"extra comma following value {last_value} removed"
            warning(f"{source.name}:{lineno}:{col} {msg}")
            state = States.seek_value

        elif st == (States.seek_value, Tokens.close_brace):
            last = len(actual_row) - 1
            last_value = actual_row[last]
            msg = f"extra comma following value {last_value} removed"
            warning(f"{source.name}:{lineno}:{col} {msg}")
            actual.append(actual_row)
            actual_row = None
            state = States.start_actual_next

        elif st == (States.post_value, Tokens.value) or \
                st == (States.post_value, Tokens.name):
            last = len(actual_row) - 1
            last_value = actual_row[last]
            msg = f"missing comma between values {last_value} and {literal}"
            warning(f"{source.name}:{lineno}:{col} {msg}")
            actual_row.append(literal)
            state = States.post_value

        elif st == (States.post_value, Tokens.comma):
            state = States.seek_value

        elif st == (States.post_value, Tokens.close_brace):
            actual.append(actual_row)
            actual_row = None
            state = States.start_actual_next

        elif st == (States.start_actual_first, Tokens.close_brace) or \
                st == (States.start_actual_next, Tokens.close_brace):
            d = {'template': template,
                 'comments': comments,
                 'formal': formal,
                 'actual': actual,
                 'eos_comment': eos_comment}
            result.append(d)
            template = None
            comments = None
            formal = None
            actual = None
            eos_comment = None

            state = States.seek_file

        else:
            msg = "unexpected state/token combination"
            raise ParseError(f"{source.name}:{lineno}:{col} {msg}: {state.name}/{token.name}")

    return result


# -----------------------------------------------------------------------------
#
def process(source, target, indent, spacing, width):
    """ Main tidy functionality here.
        source and target are open file objects
        This called directly for stdin/stdout
    """
    sub_file = process_source(source)
    generate(sub_file, target=target, indent=indent, spacing=spacing, width=width)


# -----------------------------------------------------------------------------
#
def process_file(filename, indent, spacing, width):
    """ Handles file opening/closing of filename
    """

    # We complete the read of the contents of filename and convert to the internal
    # representation before we re-open to write again. If an exception is raised
    # while reading, we do not re-open the file for writing, and the file remains
    # unchanged.
    #
    with open(filename, 'r') as source:
        sub_file = process_source(source)

    with open(filename, 'w') as target:
        generate(sub_file, target=target, indent=indent, spacing=spacing, width=width)

# end
