"""Machinery for interspersing lines of text with linked and colored regions

The typical entrypoints are es_lines() and html_line().

Within this file, "tag" means a tuple of (file-wide offset, is_start, payload).

"""
import cgi
try:
    from itertools import compress
except ImportError:
    from itertools import izip
    def compress(data, selectors):
        return (d for d, s in izip(data, selectors) if s)
import json
from warnings import warn

from jinja2 import Markup


class Line(object):
    """Representation of a line's beginning and ending as the contents of a tag

    Exists to motivate the balancing machinery to close all the tags at the end
    of every line (and reopen any afterward that span lines).

    """
    sort_order = 0  # Sort Lines outermost.

    def __repr__(self):
        return 'Line()'

LINE = Line()


class TagWriter(object):
    """A thing that hangs onto a tag's payload (like the class of a span) and
    knows how to write its opening and closing tags"""

    def __init__(self, payload):
        self.payload = payload

    # __repr__ comes in handy for debugging.
    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self.payload)


class Region(TagWriter):
    """Thing to open and close <span> tags"""
    sort_order = 2  # Sort Regions innermost, as it doesn't matter if we split
                    # them.

    def es(self):
        return self.payload


class Ref(TagWriter):
    """Thing to open and close <a> tags"""
    sort_order = 1

    def es(self):
        menuitems, hover = self.payload
        ret = {'menuitems': menuitems}
        if hover:
            ret['hover'] = hover
        return ret


def balanced_tags(tags):
    """Come up with a balanced series of tags which express the semantics of
    the given sorted interleaved ones.

    Return an iterable of (point, is_start, Region/Reg/Line) without any
    (pointless) zero-width tag spans. The output isn't necessarily optimal, but
    it's fast and not embarrassingly wasteful of space.

    """
    return without_empty_tags(balanced_tags_with_empties(tags))


def without_empty_tags(tags):
    """Filter zero-width tagged spans out of a sorted, balanced tag stream.

    Maintain tag order. Line break tags are considered self-closing.

    """
    buffer = []  # tags
    depth = 0

    for tag in tags:
        point, is_start, payload = tag

        if is_start:
            buffer.append(tag)
            depth += 1
        else:
            top_point, _, top_payload = buffer[-1]
            if top_payload is payload and top_point == point:
                # It's a closer, and it matches the last thing in buffer and, it
                # and that open tag form a zero-width span. Cancel the last thing
                # in buffer.
                buffer.pop()
            else:
                # It's an end tag that actually encloses some stuff.
                buffer.append(tag)
            depth -= 1

            # If we have a balanced set of non-zero-width tags, emit them:
            if not depth:
                for b in buffer:
                    yield b
                del buffer[:]


def balanced_tags_with_empties(tags):
    """Come up with a balanced series of tags which express the semantics of
    the given sorted interleaved ones.

    Return an iterable of (point, is_start, Region/Reg/Line), possibly
    including some zero-width tag spans. Each line is enclosed within Line tags.

    :arg tags: An iterable of (offset, is_start, payload) tuples, with one
        closer for each opener but possibly interleaved. There is one tag for
        each line break, with a payload of LINE and an is_start of False. Tags
        are ordered with closers first, then line breaks, then openers.

    """
    def close(to=None):
        """Return an iterable of closers for open tags up to (but not
        including) the one with the payload ``to``."""
        # Loop until empty (if we're not going "to" anything in particular) or
        # until the corresponding opener is at the top of the stack. We check
        # that "to is None" just to surface any stack-tracking bugs that would
        # otherwise cause opens to empty too soon.
        while opens if to is None else opens[-1] is not to:
            intermediate_payload = opens.pop()
            yield point, False, intermediate_payload
            closes.append(intermediate_payload)

    def reopen():
        """Yield open tags for all temporarily closed ones."""
        while closes:
            intermediate_payload = closes.pop()
            yield point, True, intermediate_payload
            opens.append(intermediate_payload)

    opens = []  # payloads of tags which are currently open
    closes = []  # payloads of tags which we've had to temporarily close so we could close an overlapping tag
    point = 0

    yield 0, True, LINE
    for point, is_start, payload in tags:
        if is_start:
            yield point, is_start, payload
            opens.append(payload)
        elif payload is LINE:
            # Close all open tags before a line break (since each line is
            # wrapped in its own <code> tag pair), and reopen them afterward.
            for t in close():  # I really miss "yield from".
                yield t

            # Since preserving self-closing linebreaks would throw off
            # without_empty_tags(), we convert to explicit closers here. We
            # surround each line with them because empty balanced ones would
            # get filtered out.
            yield point, False, LINE
            yield point, True, LINE

            for t in reopen():
                yield t
        else:
            # Temporarily close whatever's been opened between the start tag of
            # the thing we're trying to close and here:
            for t in close(to=payload):
                yield t

            # Close the current tag:
            yield point, False, payload
            opens.pop()

            # Reopen the temporarily closed ones:
            for t in reopen():
                yield t
    yield point, False, LINE


def tag_boundaries(refs, regions):
    """Return a sequence of (offset, is_start, Region/Ref/Line) tuples.

    Basically, split the atomic tags that come out of plugins into separate
    start and end points, which can then be thrown together in a bag and sorted
    as the first step in the tag-balancing process.

    Like in Python slice notation, the offset of a tag refers to the index of
    the source code char it comes before.

    :arg refs: An iterable (doesn't have to be a list)
    :arg regions: An iterable (doesn't have to be a list)

    """
    for intervals, cls in [(regions, Region), (refs, Ref)]:
        for start, end, data in intervals:
            tag = cls(data)
            # Filter out zero-length spans which don't do any good and
            # which can cause starts to sort after ends, crashing the tag
            # balancer. Incidentally filter out spans where start tags come
            # after end tags, though that should never happen.
            #
            # Also filter out None starts and ends. I don't know where they
            # come from. That shouldn't happen and should be fixed in the
            # plugins.
            if (start is not None and start != -1 and
                    end is not None and end != -1 and
                    start < end):
                yield start, True, tag
                yield end, False, tag


def line_boundaries(line_offsets):
    """Return a tag for the end of each line in a string.

    :arg line_offsets: list of offsets of the start of each line from the start
    of the file

    Endpoints and start points are coincident: right after a (universal)
    newline.

    """
    for offset in line_offsets:
        yield offset, False, LINE
        yield offset, True, LINE


def non_overlapping_refs(tags):
    """Yield a False for each Ref in ``tags`` that overlaps a subsequent one,
    a True for the rest.

    Assumes the incoming tags, while not necessarily well balanced, have the
    start tag come before the end tag, if both are present. (Lines are weird.)

    """
    blacklist = set()
    open_ref = None
    for point, is_start, payload in tags:
        if isinstance(payload, Ref):
            if payload in blacklist:  # It's the evil close tag of a misnested tag.
                blacklist.remove(payload)
                yield False
            elif open_ref is None:  # and is_start: (should always be true if input is sane)
                assert is_start
                open_ref = payload
                yield True
            elif open_ref is payload:  # it's the closer
                open_ref = None
                yield True
            else:  # It's an evil open tag of a misnested tag.
                warn('htmlifier plugins requested overlapping <a> tags. Fix the plugins.')
                blacklist.add(payload)
                yield False
        else:
            yield True


def remove_overlapping_refs(tags):
    """For any series of <a> tags that overlap each other, filter out all but
    the first.

    There's no decent way to represent that sort of thing in the UI, so we
    don't support it.

    :arg tags: A list of (point, is_start, payload) tuples, sorted by point.
        The tags do not need to be properly balanced.

    """
    # Reuse the list so we don't use any more memory.
    i = None
    for i, tag in enumerate(compress(tags, non_overlapping_refs(tags))):
        tags[i] = tag
    if i is not None:
        del tags[i + 1:]


def nesting_order((point, is_start, payload)):
    """Return a sorting key that places coincident Line boundaries outermost,
    then Ref boundaries, and finally Region boundaries.

    The Line bit saves some empty-tag elimination. The Ref bit saves splitting
    an <a> tag (and the attendant weird UI) for the following case::

        Ref    ____________  # The Ref should go on the outside.
        Region _____

    Other scenarios::

        Reg _______________        # Would be nice if Reg ended before Ref
        Ref      ________________  # started. We'll see about this later.

        Reg _____________________  # Works either way
        Ref _______

        Reg _____________________
        Ref               _______  # This should be fine.

        Reg         _____________  # This should be fine as well.
        Ref ____________

        Reg _____
        Ref _____  # This is fine either way.

    Also, endpoints sort before coincident start points to save work for the
    tag balancer.

    """
    return point, is_start, (payload.sort_order if is_start else
                             -payload.sort_order)

def finished_tags(line_offsets, refs, regions):
    """Return an ordered iterable of properly nested tags which fully describe
    the refs and regions and their places in a file's text.

    :arg text: Unicode text of the file to htmlify. ``build_lines`` may not be
        used on binary files.

    """
    # Plugins return unicode offsets, not byte ones.

    #import pdb; pdb.set_trace()
    # Get start and endpoints of intervals:
    tags = list(tag_boundaries(refs, regions))

    tags.extend(line_boundaries(line_offsets))

    # Sorting is actually not a significant use of time in an actual indexing
    # run.
    tags.sort(key=nesting_order)  # balanced_tags undoes this, but we tolerate
                                  # that in html_lines().
    remove_overlapping_refs(tags)
    return balanced_tags(tags)


def tags_per_line(flat_tags):
    """
    Yield a list of tags for each line by breaking up the stream of flat_tags
    at LINE tag boundaries.
    """
    tags = []
    for t in flat_tags:
        point, is_start, payload = t
        if payload is LINE:
            if is_start:
                yield tags
                tags = []
        else:
            tags.append(t)

def es_lines(tags):
    """Yield a list of dicts, one per source code line, that can be indexed
    into the ``tags`` field of the ``line`` doctype in elasticsearch.

    TODO:
    Convert from the per-file offsets of refs() and regions() to per-line ones.
    We include explicit, separate closers in the hashes because, in order to
    divide tags into line-based sets (including cutting some in half if they
    spanned lines), we already had to do all the work of ordering and
    balancing. There's no sense doing that again at request time.

    :arg tags: An iterable of ordered, non-overlapping, non-empty tag
        boundaries with Line tags at (and outermost at) the index of the
        end of each line.

    """
    # Map of payload to {start, end} per line.
    for line in tags_per_line(tags):
        payloads = {}
        for point, is_start, payload in line:
            if is_start:
                payloads[payload] = {'start': point}
            else:
                payloads[payload]['end'] = point
        yield [{'payload': payload.es(), 'start': pos['start'], 'end':
            pos['end']} for payload, pos in payloads.iteritems()]
    # tags always ends with a LINE closer, so we don't need any additional
    # yield here to catch remnants.

def triples_from_es_refs(es_refs):
    """
    Undo list of lists of es refs per lines back to (start, end, payload) triples.
    """
    for line in es_refs:
        for item in line:
            ref = (item['payload']['menuitems'], item['payload'].get('hover'))
            yield (item['start'], item['end'], ref)

def triples_from_es_regions(es_regions):
    """
    Undo list of lists es regions back to (start, end, payload) triples.
    """
    # TODO: refactor with triples_from_es_regions
    for line in es_regions:
        for item in line:
            #import pdb; pdb.set_trace()
            region = item['payload']
            yield (item['start'], item['end'], region)

def html_line(text, tags, bof_offset):
    """Return a line of Markup, interleaved with the refs and regions that
    decorate it.

    :arg tags: An ordered iterable of balanced tags from finished_tags
    :arg text: The unicode text to decorate
    :arg bof_offset: Unicode codepoint position of start of line in file.

    """
    #import pdb; pdb.set_trace()
    def segments(text, tags):
        #import pdb; pdb.set_trace()
        up_to = 0
        for (pos, is_start, payload) in tags:
            pos -= bof_offset
            yield cgi.escape(text[up_to:pos].strip(u'\r\n'))
            up_to = pos
            if not is_start:  # It's a closer. Most common.
                yield '</a>' if isinstance(payload, Ref) else '</span>'
            elif isinstance(payload, Region):  # It's a span.
                yield u'<span class="%s">' % cgi.escape(payload.payload, True)
            else:  # It's a menu.
                menu, hover = payload.payload
                menu = cgi.escape(json.dumps(menu), True)
                if hover is not None:
                    title = ' title="' + cgi.escape(hover, True) + '"'
                else:
                    title = ''
                yield u'<a data-menu="%s"%s>' % (menu, title)
        yield text[up_to:]

    return Markup(u''.join(segments(text, tags)))

def lines_and_offsets(contents):
    """
    Yield (line, bof_offset) for each line in contents, where line keeps its
    ending newline.
    """
    lines = contents.splitlines(True)
    chars = 0
    for line in lines:
        yield line, chars
        chars += len(line)

def reconstitute_contents(lines_and_offsets):
    """
    Return a reconstituted contents from the lines, where line endings are
    guessed based on offsets. Reconstituted contents will not end with a new
    line.

    :arg iterable lines_offsets: Tuples (line, offset), where line does not
        have ending newline and offset is the byte position of the start of the
        line from BOF.
    """
    def lines_with_newlines():
        # Track the previous offset. len(reconstituted line) = next_offset - its_offset
        previous_offset = previous_line = None
        for line, offset in lines_and_offsets:
            if previous_line is not None:
                length_with_newline = offset - previous_offset
                length_of_newline = length_with_newline - len(previous_line)
                yield previous_line + '\n' if length_of_newline == 1 else '\r\n'
            previous_offset = offset
            previous_line = line
        # We check here in case the file is empty.
        if previous_line is not None:
            yield line

    return ''.join(lines_with_newlines())
