"""Administration from the server's shell.

    docker compose exec api python -m app.cli create-admin you@example.com

The first admin takes over the local user (id 1) when it has no email yet, so the data of a
self-hosted install that becomes a hosted service stays with its owner. The password is
asked for interactively (or read from standard input with --password-stdin), never passed
on the command line, where it would end up in the shell history.
"""

import argparse
import getpass
import sys

from app import auth, migrate
from app.db import SessionLocal
from app.models import LOCAL_USER_ID, User

LINE_END = "\r\n"


def create_admin(email: str, password_stdin: bool = False) -> None:
    email = email.strip().lower()
    if password_stdin:  # for scripts: one line on standard input
        password = sys.stdin.readline().rstrip(LINE_END)
    else:
        password = getpass.getpass("Contraseña: ")
        if getpass.getpass("Repítela: ") != password:
            sys.exit("Las contraseñas no coinciden")
    if len(password) < auth.MIN_PASSWORD:
        sys.exit(f"La contraseña necesita al menos {auth.MIN_PASSWORD} caracteres")
    migrate.upgrade()
    with SessionLocal() as session:
        user = auth.find_user(session, email)
        if user is None:
            local = session.get(User, LOCAL_USER_ID)
            user = local if local is not None and local.email is None else User()
            if user.id is None:
                session.add(user)
        user.email, user.password_hash, user.is_admin = email, auth.hash_password(password), True
        session.commit()
        print(f"Administración: {email} (usuario {user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="create an admin account, or make an account admin")
    admin.add_argument("email")
    admin.add_argument("--password-stdin", action="store_true", help="read the password from standard input")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.password_stdin)


if __name__ == "__main__":
    main()
