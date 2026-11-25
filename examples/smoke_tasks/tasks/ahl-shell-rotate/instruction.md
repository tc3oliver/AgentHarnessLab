Write an executable bash script `/app/rotate.sh`, used as `/app/rotate.sh DIR KEEP`.

In `DIR`, look only at regular files whose names end in `.log` (not in subdirectories). Sort them by file
name in descending order (names contain dates like `app-2024-03-01.log`, so the newest sorts first). Keep
the first `KEEP` files and delete the rest. Never touch other files or directories. File names may contain
spaces. If there are `KEEP` or fewer log files, delete nothing. `KEEP` of `0` deletes every `.log` file.
Print nothing to stdout. Exit with status 2 and a message on stderr if `DIR` is not a directory.
