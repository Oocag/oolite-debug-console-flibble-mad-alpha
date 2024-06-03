#  Created by Mister Flibble 20240531
#  (c) 2024 Mister Flibble CC-by-NC-SA 4

"""
Parses cli args. Holds defaults for them. Also determines platform/frozen
"""


# Do not import anything which will is intended to be later modified by this.

from pathlib import Path
import re
import click
import os
#Might want to do this properly, with __version__ file.
from debugGUI._version import __version__

# Will need to know platform here.
# so moved platform check here to avoid circular reference vs constants.
import sys
p = dict (
  f = hasattr(sys, 'frozen'),  ## cannot test until build exe
  w = sys.platform.startswith('win'),
  l = sys.platform.startswith('linux'),
  m = sys.platform.startswith('darwin')
)

# get home path
#  homepath=Path.home().as_posix() + "/GNUstep/Defaults/"
#### CRAP IDEA. This is all GNUsteppy stuff, not the user configs.

# def logs hist : 
#  Mac ~/Library/Logs/Oolite/
#  Win Mixed messages on wiki at https://wiki.alioth.net/index.php/Latest.log
#   and https://github.com/OoliteProject/OoliteStarter/blob/master/src/main/java/oolite/starter/Configuration.java#L171
#   so path of least resistance is $HOME .Oolite/Logs
#  Lin ~/.Oolite/Logs



# set up globals with sane defaults using same names as click
g = dict(
  base = "OoDC",
  cpath = os.path.join(Path.home().as_posix(), '.OoDC/Configs'),
  lpath = os.path.join(Path.home().as_posix(), '.OoDC/Logs'),
  cext = 'cfg',
  hext = 'dat',
  lext = 'log',
  stderr = False,
)

##### This will cause unknown arguments to spit out full help.
##### Monkey patch UsageError in click from:-
#####  https://stackoverflow.com/questions/53130864/python-click-how-to-print-full-help-details-on-usage-error
#from click.exceptions import UsageError
#from click._compat import get_text_stderr
#from click.utils import echo
#
#def _show_usage_error(self, file=None):
#  if file is None:
#    file = get_text_stderr()
#  color = None
#  if self.ctx is not None:
#    color = self.ctx.color
#    echo(self.ctx.get_help() + '\n', file=file, color=color)
#  echo('Error: %s' % self.format_message(), file=file, color=color)
#
#UsageError.show = _show_usage_error
##### End monkey patch

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help', '-?'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.version_option(
  __version__,
  "--version",
  "-v"
)

@click.option("--base","-b",
  help=( "Base filename for config/log :  Default=" +
    g['base'] + " (filter\u00a0A-Za-z0-9_-)"
  ), type=str)
@click.option("--cpath","-c",
  help=(
    "Directory for config files. " +
    "Will be created if missing. Default=" + g['cpath']),
      type=click.Path())
@click.option("--lpath","-l",
  help=(
    "Directory for log files. " +
    "Will be created if missing. Default=" + g['lpath']),
      type=click.Path())
@click.option("--cext","-x",
  help=("Config file extension. Default=" +
  str(g['cext']) + " (filter\u00a0A-Za-z0-9)"), type=str)
@click.option("--lext","-y",
  help=("Log file extension. Default=" +
  str(g['lext']) +" (filter\u00a0A-Za-z0-9)"), type=str)
@click.option("--hext","-z",
  help=("History file extension. Default=" +
  str(g['hext'])+" (filter\u00a0A-Za-z0-9)"), type=str)
@click.option("--stderr","-e",
  help=(
  "Send log to stderr instead of file (not yet implemented). Default=" +
  str(g['stderr'])), is_flag=True) #seems to like file OR dir.

def cli(base,cpath,lpath,cext,lext,hext,stderr):
  """Oolite Debug Console : OoDC (Oodyssey)
  \b
  Config files and logs will be stored in a location.
  Let's see if we can make that location more predictable.

  Exits on help/version/error.
  """
  global g

  #Parse dirs. Use defaults if not in cli args.
  isDir(g['cpath'],'cpath') if cpath is None else isDir(cpath,'cpath') 
  isDir(g['lpath'],'cpath') if lpath is None else isDir(lpath,'lpath')

  if base is not None:
    if re.match("^[A-Za-z0-9_-]*$", base):
      g['base'] = base
    else:
      raise click.BadParameter(
        'Invalid base filename. Only A-Za-z0-9_- are accepted.\n',
        param_hint=["--base"])

  if stderr:
    g['stderr'] = True

  isExt(cext,'cext')
  isExt(lext,'lext')
  isExt(hext,'hext')

#  click.echo(f"cpath: {cpath!r}")
#  click.echo(f"lpath: {lpath!r}")
#  click.echo(f"base: {base!r}")
#  click.echo(f"stderr: {stderr!r}")
#  click.echo(f"cext: {cext!r}")
#  click.echo(f"lext: {lext!r}")
#  click.echo(f"hext: {hext!r}")
  click.echo("Command line parse good. Continuing.")

  print(g)

  global shouldquit
  shouldquit=False

def exec():

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


def isDir(thisdir,key):
  """
  Sanity check directory name and either
   add it to the dict, or fail with sane err.
  """
  global g
  if Path(thisdir).exists():
    if Path(thisdir).is_dir():
      g[key] = thisdir
    elif Path(thisdir).is_file():
      raise click.BadParameter( (
        'Specified path "' + thisdir + '"is file. Directory expected.\n'
        ), param_hint=["--" + key]
      )
    else:
      raise click.BadParameter( (
        'Invalid path "' + thisdir ), param_hint=["--" + key])
        # May need to create dir. Prompt for it, and add a no-prompt option?
  else:
    print('Could not find directory "' + thisdir 
      + ' for option --' + key + '. Attempting to create it.')
    try:
      os.makedirs(thisdir, exist_ok = True)
      print("Directory " , thisdir ,  " Created ")
    except:
      raise click.BadParameter( (
        'Path "' + thisdir + '" does not exist and could not be created.\n'
         ), param_hint=["--" + key])


def isExt(ext,key):
  """
  Sanity check file extension and either add it to the dict,
   or fail with sane err.
  Currently only checks for alphanumeric, so can be any length.
  """
  global g
  if ext is not None:
    if re.match("^[A-Za-z0-9]*$", ext):
      g[key] = ext
    else:
      raise click.BadParameter('Invalid file extension.\n', param_hint=["--" + key])


exec()


#  con.BASE_FNAME = base
#if __name__ == '__main__':
#    exec()


