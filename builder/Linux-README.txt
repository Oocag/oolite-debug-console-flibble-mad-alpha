
This will build an app tarball, with an executable that will work where python
 is unavailable.

It is aimed at Debian/Ubuntu systems.

It may work on other dists if the requirements are met and using 'nocheck'.


Short version:

    tar -xpzf Linux.tar
    cd Linux
    ./make.sh

Test:

    ./OoDC

If rebuilding for any reason, delete the build directory.

To install to .local in a home directory:

    tar -C $HOME/.local/ -xpzf OoDC-*-linux-installable.tar.gz

Detailed info:

Unpack the Linux.tar.gz in this folder.
The path relative to the what it's building is important due to symlinks.

    tar -xpzf Linux.tar.gz

This will create a directory "Linux", containing:-

    make.sh install-tree

make.sh is the script used to make the executable from the python source.

If run in the Linux directory as

    ./make.sh

The script will initially run apt install for packages it depends on.

    apt install python3-tk python3-pip python3-venv binutils

For most users, this will involve a prompt to authenticate.

After the first run (or if you know the packages are already installed),
 this step can be skipped by running the script with nocheck as an arg1:

    ./make.sh nocheck

Any other arg1 will be used as the output name for the tarball. Take care!

Either way, it will go on to:
    Create a "build" directory.
    Create a python3 venv in it.
    Activate the venv.
    Use pip inside the venv to install python dependencies and pyinstaller.
    Compile an executable of the project.
    Move the executable into the current (Linux) directory for quick testing.
    Make an installable tarball.

install-tree
    A directory structure used to make installer tarballs.
    Contains icon, .desktop file, and a symlink to the executable that gets
     made by make.sh. this will be dereferenced by tar when the installable
     tarball gets made.
