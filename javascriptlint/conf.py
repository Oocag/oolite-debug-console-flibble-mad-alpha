# vim: ts=4 sw=4 expandtab
import os
import unittest

from . import fs
from . import util
from . import version
from . import lintwarnings

_DISABLED_WARNINGS = (
   'block_without_braces',
   'function_name_missing',
   'function_name_mismatch',
   'trailing_whitespace',
)

def _getwarningsconf():
    lines = []
    for name in sorted(lintwarnings.warnings.keys()):
        message = lintwarnings.warnings[name]
        sign = '+'
        if name in _DISABLED_WARNINGS:
            sign = '-'
        assert len(name) < 29
        lines.append(sign + name.ljust(29) + '# ' + message)
    return '\n'.join(lines)

DEFAULT_CONF = """\
#
# Configuration File for JavaScript Lint {version}
# Developed by Matthias Miller (http://www.JavaScriptLint.com)
#
# This configuration file can be used to lint a collection of scripts, or to enable
# or disable warnings for scripts that are linted via the command line.
#

### Warnings
# Enable or disable warnings based on requirements.
# Use "+WarningName" to display or "-WarningName" to suppress.
#
{warnings}


### Output format
# Customize the format of the error message.
#    __FILE__ indicates current file path
#    __FILENAME__ indicates current file name
#    __LINE__ indicates current line
#    __COL__ indicates current column
#    __ERROR__ indicates error message (__ERROR_PREFIX__: __ERROR_MSG__)
#    __ERROR_NAME__ indicates error name (used in configuration file)
#    __ERROR_PREFIX__ indicates error prefix
#    __ERROR_MSG__ indicates error message
#
# For machine-friendly output, the output format can be prefixed with
# "encode:". If specified, all items will be encoded with C-slashes.
#
# Visual Studio syntax (default):
+output-format __FILE__(__LINE__): __ERROR__
# Alternative syntax:
#+output-format __FILE__:__LINE__: __ERROR__


### Context
# Show the in-line position of the error.
# Use "+context" to display or "-context" to suppress.
#
+context


### Control Comments
# Both JavaScript Lint and the JScript interpreter confuse each other with the syntax for
# the /*@keyword@*/ control comments and JScript conditional comments. (The latter is
# enabled in JScript with @cc_on@). The /*jsl:keyword*/ syntax is preferred for this reason,
# although legacy control comments are enabled by default for backward compatibility.
#
-legacy_control_comments


### Defining identifiers
# By default, "option explicit" is enabled on a per-file basis.
# To enable this for all files, use "+always_use_option_explicit"
+always_use_option_explicit

# Define certain identifiers of which the lint is not aware.
# (Use this in conjunction with the "undeclared identifier" warning.)
#
# Common uses for webpages might be:
#+define window
#+define document


### JavaScript Version
# To change the default JavaScript version:
#+default-type text/javascript;version=1.5
#+default-type text/javascript;e4x=1

### 
# Some browsers pollute the namespace when using the "function_name_missing"
# or "function_name_mismatch" warning. Enable this option to require a
# double-underscore prefix.
#+decorate_function_name_warning

### Files
# Specify which files to lint
# Use "+recurse" to enable recursion (disabled by default).
# To add a set of files, use "+process FileName", "+process Folder\\Path\\*.js",
# or "+process Folder\\Path\\*.htm".
#
""".format(
    version=version.version,
    warnings=_getwarningsconf(),
)


class ConfError(Exception):
    def __init__(self, error):
        Exception.__init__(self, error)
        self.lineno = None
        self.path = None

class Setting:
    wants_parm = False
    wants_dir = False

class DeprecatedSetting(Setting):
    wants_parm = False
    value = None
    def load(self, enabled):
        raise ConfError('This setting is deprecated.')

class BooleanSetting(Setting):
    wants_parm = False
    def __init__(self, default):
        self.value = default
    def load(self, enabled):
        self.value = enabled

class StringSetting(Setting):
    wants_parm = True
    def __init__(self, default):
        self.value = default
    def load(self, enabled, parm):
        if not enabled:
            raise ConfError('Expected +.')
        self.value = parm

class DeclareSetting(Setting):
    wants_parm = True
    def __init__(self):
        self.value = []
    def load(self, enabled, parm):
        if not enabled:
            raise ConfError('Expected +.')
        self.value.append(parm)

class ProcessSetting(Setting):
    wants_parm = True
    wants_dir = True
    def __init__(self, recurse_setting):
        self.value = []
        self._recurse = recurse_setting
    def load(self, enabled, parm, dir):
        if dir:
            parm = os.path.join(dir, parm)
        self.value.append((self._recurse.value, parm))

class JSVersionSetting(Setting):
    wants_parm = True
    value = util.JSVersion.default()
    def load(self, enabled, parm):
        if not enabled:
            raise ConfError('Expected +.')

        self.value = util.JSVersion.fromtype(parm)
        if not self.value:
            raise ConfError('Invalid JavaScript version: %s' % parm)

class ConfSetting(Setting):
    wants_parm = True
    wants_dir = True
    def __init__(self, conf):
        self.value = None
        self._conf = conf
    def load(self, enabled, parm, dir):
        if dir:
            parm = os.path.join(dir, parm)
        self._conf.loadfile(parm)
        self.value = parm

class IncludeDirSetting(Setting):
    wants_parm = True
    wants_dir = True
    def __init__(self):
        self.value = []
    def load(self, enabled, parm, dir):
        if not dir:
            raise ConfError('The %s setting is only valid in a configuration file.' % parm)

        abs_dir = os.path.abspath(os.path.join(dir, parm))
        self.value.append(abs_dir)

class Conf:
    def __init__(self):
        recurse = BooleanSetting(False)
        self._settings = {
            'recurse': recurse,
            'output-format': StringSetting('__FILE__(__LINE__): __ERROR__'),
            'lambda_assign_requires_semicolon': DeprecatedSetting(),
            'legacy_control_comments': BooleanSetting(False),
            'jscript_function_extensions': DeprecatedSetting(),
            'always_use_option_explicit': BooleanSetting(True),
            'define': DeclareSetting(),
            'context': BooleanSetting(True),
            'process': ProcessSetting(recurse),
            'default-version': JSVersionSetting(),
            'conf': ConfSetting(self),
            'include-dir': IncludeDirSetting(),
            # SpiderMonkey warnings
            'no_return_value': BooleanSetting(True),
            'equal_as_assign': BooleanSetting(True),
            'anon_no_return_value': BooleanSetting(True),
            'decorate_function_name_warning': BooleanSetting(False),
        }
        for name in lintwarnings.warnings:
            self._settings[name] = BooleanSetting(True)
        for warning in _DISABLED_WARNINGS:
           self.loadline('-%s' % warning)

    def loadfile(self, path):
        path = os.path.abspath(path)
        conf = fs.readfile(path, 'utf-8')
        try:
            self.loadtext(conf, dir=os.path.dirname(path))
        except ConfError as error:
            error.path = path
            raise

    def loadtext(self, conf, dir=None):
        lines = conf.splitlines()
        for lineno, line in enumerate(lines):
            try:
                self.loadline(line, dir)
            except ConfError as error:
                error.lineno = lineno
                raise

    def loadline(self, line, dir=None):
        assert not '\r' in line
        assert not '\n' in line

        # Allow comments
        if '#' in line:
            line = line[:line.find('#')]
        line = line.rstrip()
        if not line:
            return

        # Parse the +/-
        if line.startswith('+'):
            enabled = True
        elif line.startswith('-'):
            enabled = False
        else:
            raise ConfError('Expected + or -.')
        line = line[1:]

        # Parse the key/parms
        name = line.split()[0].lower()
        parm = line[len(name):].lstrip()

        # Load the setting
        try:
            setting = self._settings[name]
        except KeyError as error:
            raise ConfError('Unrecognized setting: %s' % name) from error
        args = {
            'enabled': enabled
        }
        if setting.wants_parm:
            args['parm'] = parm
        elif parm:
            raise ConfError('The %s setting does not expect a parameter.' % name)
        if setting.wants_dir:
            args['dir'] = dir
        setting.load(**args)

    def __getitem__(self, name):
        if name == 'paths':
            name = 'process'
        elif name == 'declarations':
            name = 'define'
        return self._settings[name].value

class TestConf(unittest.TestCase):
    def testDefaultConf(self):
        # Make sure the string version corresponds with the code.
        fromstr = Conf()
        fromstr.loadtext(DEFAULT_CONF)
        fromcode = Conf()
        settings = set(list(fromcode._settings.keys()) + list(fromstr._settings.keys()))
        for setting in settings:
            self.assertEqual(fromcode[setting], fromstr[setting],
                              'Mismatched defaults for %s' % setting)

