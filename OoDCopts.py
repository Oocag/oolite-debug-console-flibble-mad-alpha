#  Created by Mister Flibble 20240531
#  (c) 2024 Mister Flibble CC-by-NC-SA 4

import debugGUI.constants as con
import re
from _version import __version__

#defaultPath=
dPath="/tmp" #default path
dBase=con.BASE_FNAME # default basename
STDerr=False

#defaultLfile
# print(defaultCfile)

import click

##### This will cause unknown arguments to spit out full help.
##### Monkey patch UsageError in click from:-
#####  https://stackoverflow.com/questions/53130864/python-click-how-to-print-full-help-details-on-usage-error
from click.exceptions import UsageError
from click._compat import get_text_stderr
from click.utils import echo

def _show_usage_error(self, file=None):
  if file is None:
    file = get_text_stderr()
  color = None
  if self.ctx is not None:
    color = self.ctx.color
    echo(self.ctx.get_help() + '\n', file=file, color=color)
  echo('Error: %s' % self.format_message(), file=file, color=color)

UsageError.show = _show_usage_error
##### End monkey patch

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help', '-?'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.version_option(
  __version__,
  "--version",
  "-v"
)

@click.option("--base","-b", help=("Base filename for config/log. Only characters A-Za-z0-9_- are accepted. Default=" + dBase), type=str)
@click.option("--path","-p", help=("Directory for config/log files. Must exist. Default=" + dPath), type=click.Path()) #seems to like file OR dir.
@click.option("--stderr","-e", help=("Send log to stderr instead of file. Default=" + str(STDerr)), is_flag=True) #seems to like file OR dir.


def cli(path,base,stderr):
  """Oolite Debug Console : OoDC (Oodyssey)
  \b
  Config files and logs will be stored in a location.
  Let's see if we can make that location more predictable.
  """
  if path is not None:
    from pathlib import Path
    if Path(path).exists():       # This determines if the string input is a valid path
      if Path(path).is_dir():
        print("path is dir\n")
        global dPath
        dPath = path
      elif Path(path).is_file():
        raise click.BadParameter('Specified path is file. Directory expected.', param_hint=["--path"])
      else:
        raise click.BadParameter('Invalid path', param_hint=["--path"])
        #Explore creating path. Maybe prompt for it, and add a no-prompt option.

  if base is not None:
    if re.match("^[A-Za-z0-9_-]*$", base):
      global dBase
      dBase = base
    else:
      raise clickBadParameter('Invalid base filename. only A-Za-z0-9_- are accepted.', param_hint=["--base"])

  if stderr:
    global STDerr
    STDerr=True

  click.echo(f"path: {path!r}")
  click.echo(f"base: {base!r}")
  click.echo(f"stderr: {stderr!r}")
  click.echo("Command line empty or args good. Continuing.")
  global shouldquit
  shouldquit=False

def exec():

  print("\nParsing command line args. Testing only.\nNone of this is actually used yet.\nExits on help/version/error.")

  global shouldquit
  shouldquit=True

  try:
    cli()
  except SystemExit as e:
    if e.code != 0:
      raise

  if shouldquit:
#    quit() #breaks if frozen
    import sys
    sys.exit(1)
  else:
    return(dPath,dBase,STDerr)

if __name__ == '__main__':
    exec()
