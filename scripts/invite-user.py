#!/usr/bin/env python3
"""
The Orbital — invite management CLI
Manages the invites table in Supabase (via service role key).

Usage:
  python scripts/invite-user.py add alice@example.com [--invited-by "Olle"]
  python scripts/invite-user.py list
  python scripts/invite-user.py revoke alice@example.com

Requires SUPABASE_SERVICE_ROLE_KEY in the environment (or .env file).
"""

import os
import sys
import argparse
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass  # dotenv not installed — rely on shell env vars

try:
    from supabase import create_client
except ImportError:
    print("Error: 'supabase' package not installed. Run: pip install supabase")
    sys.exit(1)


SUPABASE_URL = "https://lathlnothoosbwrvxtel.supabase.co"


def get_admin_client():
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        print("Error: SUPABASE_SERVICE_ROLE_KEY environment variable not set.")
        print("  Get it from: https://supabase.com/dashboard/project/lathlnothoosbwrvxtel/settings/api")
        sys.exit(1)
    return create_client(SUPABASE_URL, key)


def cmd_add(args):
    email = args.email.strip().lower()
    client = get_admin_client()

    result = client.table("invites").upsert(
        {
            "email": email,
            "invited_by": args.invited_by or None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="email",
    ).execute()

    print(f"✓ Invite added for {email}")
    if args.invited_by:
        print(f"  Invited by: {args.invited_by}")


def cmd_list(args):
    client = get_admin_client()
    result = client.table("invites").select("*").order("created_at").execute()
    invites = result.data

    if not invites:
        print("No invites found.")
        return

    print(f"{'Email':<36} {'Invited by':<20} {'Created':<12} {'Used'}")
    print("-" * 80)
    for inv in invites:
        used = inv.get("used_at")
        used_str = used[:10] if used else "—"
        by = inv.get("invited_by") or "—"
        created = (inv.get("created_at") or "")[:10]
        print(f"{inv['email']:<36} {by:<20} {created:<12} {used_str}")

    print(f"\n{len(invites)} total ({sum(1 for i in invites if i.get('used_at'))} used)")


def cmd_revoke(args):
    email = args.email.strip().lower()
    client = get_admin_client()

    result = client.table("invites").delete().eq("email", email).execute()
    deleted = result.data

    if deleted:
        print(f"✓ Invite revoked for {email}")
    else:
        print(f"  No invite found for {email}")


def main():
    parser = argparse.ArgumentParser(description="The Orbital — invite management")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add an invite for an email address")
    add_p.add_argument("email", help="Email address to invite")
    add_p.add_argument("--invited-by", metavar="NAME", help="Who is inviting this person (optional note)")
    add_p.set_defaults(func=cmd_add)

    list_p = sub.add_parser("list", help="List all invites")
    list_p.set_defaults(func=cmd_list)

    revoke_p = sub.add_parser("revoke", help="Revoke an invite")
    revoke_p.add_argument("email", help="Email address to revoke")
    revoke_p.set_defaults(func=cmd_revoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
