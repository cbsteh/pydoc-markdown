# Copyright (c) 2017  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
This module provides implementations to load documentation information from
an identifier as it is specified in the `pydocmd.yml:generate` configuration
key. A loader basically takes care of loading the documentation content for
that name, but is not supposed to apply preprocessing.
"""

import inspect
from textwrap import dedent

from six.moves import range

from .document import Section
from .imp import import_object_with_scope

# Check if an object (o) is a namedtuple type
def isnamedtuple(o):
    bnt = (hasattr(o, "_fields") and hasattr(o, "_asdict") and callable(o._asdict))
    return bnt


class PythonLoader(object):
    """
    Expects absolute identifiers to import with #import_object_with_scope().
    """

    def __init__(self, config):
        self.config = config

    def load_section(self, section):
        """
        Loads the contents of a #Section. The `section.identifier` is the name
        of the object that we need to load.

        # Arguments
          section (Section): The section to load. Fill the `section.title` and
            `section.content` values. Optionally, `section.loader_context` can
            be filled with custom arbitrary data to reference at a later point.
        """

        assert section.identifier is not None
        obj, scope = import_object_with_scope(section.identifier)

        if '.' in section.identifier:
            default_title = section.identifier.rsplit('.', 1)[1]
        else:
            default_title = section.identifier

        # Substitute name '__init__' with 'Constructor'
        title = getattr(obj, '__name__', default_title)
        if title == '__init__':
            title = 'Constructor __init__'
        section.title = title

        # section.title = getattr(obj, '__name__', default_title)
        section.content = dedent(getattr(obj, '__doc__', None) or '')
        section.loader_context = {'obj': obj, 'scope': scope}

        # Identify the object as class, function, or namedtuple and append type to title
        if isnamedtuple(obj):
            section.title += ' namedtuple'
        elif inspect.isclass(obj):
            section.title += ' class'
        elif callable(obj) and not inspect.isclass(scope):
            section.title += ' function'

        # Add the function signature in a code-block.
        # Ignore namedtuple signature
        if callable(obj) and not ('namedtuple' in section.content):
            sig = get_function_signature(obj, scope if inspect.isclass(scope) else None)
            # Correct the class docstring bug
            if not inspect.isclass(obj):
                section.content = '```python\n{}\n```\n'.format(sig) + section.content


def get_function_signature(function, owner_class=None, show_module=False):
    isclass = inspect.isclass(function)

    # Get base name.
    name_parts = []
    if show_module:
        name_parts.append(function.__module__)
    if owner_class:
        name_parts.append(owner_class.__name__)
    # Remove '__init__' from constructor name and signature
    if function.__name__ != '__init__':
        name_parts.append(function.__name__)
    name = '.'.join(name_parts)

    # Commented out two lines below to correct the constructor docstring bug
    # if isclass:
    #   function = function.__init__
    if hasattr(inspect, 'signature'):
        sig = str(inspect.signature(function))
    else:
        argspec = inspect.getargspec(function)
        # Generate the argument list that is separated by colons.
        args = argspec.args[:]
        if argspec.defaults:
            offset = len(args) - len(argspec.defaults)
            for i, default in enumerate(argspec.defaults):
                args[i + offset] = '{}={!r}'.format(args[i + offset], argspec.defaults[i])
        if argspec.varargs:
            args.append('*' + argspec.varargs)
        if argspec.keywords:
            args.append('**' + argspec.keywords)
        sig = '(' + ', '.join(args) + ')'

    return name + sig
