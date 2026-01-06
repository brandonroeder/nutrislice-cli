#!/usr/bin/env python3
"""
Nutrislice School Menu CLI Tool
Fetches daily breakfast/lunch menus from any Nutrislice-powered school district.

API Structure:
https://{district}.api.nutrislice.com/menu/api/weeks/school/{school-slug}/menu-type/{menu-type}/{year}/{month}/{day}/
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

import requests


class NutrisliceClient:
    """Client for fetching school menus from Nutrislice API."""

    def __init__(self, district: str):
        self.district = district
        self.base_url = f"https://{district}.api.nutrislice.com"
        self._schools_cache: list[dict] | None = None

    def fetch_schools(self) -> list[dict]:
        """Fetch list of schools for this district from the API."""
        if self._schools_cache is not None:
            return self._schools_cache

        url = f"{self.base_url}/menu/api/schools"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self._schools_cache = response.json()
            return self._schools_cache
        except requests.RequestException as e:
            print(f"Error fetching schools for district '{self.district}': {e}", file=sys.stderr)
            return []

    def resolve_school(self, query: str) -> str | None:
        """Resolve a partial school name to the full slug.

        Matching priority:
        1. Exact slug match
        2. Slug starts with query
        3. Query found in slug
        4. Query found in school name (case-insensitive)

        Returns None if no match found, or if multiple ambiguous matches.
        """
        schools = self.fetch_schools()
        if not schools:
            return None

        query_lower = query.lower().strip()

        # Try exact match first
        for school in schools:
            if school["slug"] == query_lower:
                return school["slug"]

        # Try prefix match
        prefix_matches = [s for s in schools if s["slug"].startswith(query_lower)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]["slug"]

        # Try substring match in slug
        substring_matches = [s for s in schools if query_lower in s["slug"]]
        if len(substring_matches) == 1:
            return substring_matches[0]["slug"]

        # Try substring match in name
        name_matches = [s for s in schools if query_lower in s["name"].lower()]
        if len(name_matches) == 1:
            return name_matches[0]["slug"]

        # Multiple matches - show them to the user
        all_matches = list({s["slug"] for s in prefix_matches + substring_matches + name_matches})
        if all_matches:
            print(f"Ambiguous school name '{query}'. Did you mean one of these?", file=sys.stderr)
            for slug in sorted(all_matches)[:10]:
                school = next(s for s in schools if s["slug"] == slug)
                print(f"  {slug:40} ({school['name']})", file=sys.stderr)
            return None

        return None

    def get_menu_url(self, school: str, menu_type: str, date: datetime) -> str:
        """Build the API URL for a specific school, menu type, and date."""
        return f"{self.base_url}/menu/api/weeks/school/{school}/menu-type/{menu_type}/{date.year}/{date.month:02d}/{date.day:02d}/"

    def fetch_menu(self, school: str, menu_type: str, date: datetime) -> dict:
        """Fetch menu data from the API."""
        url = self.get_menu_url(school, menu_type, date)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching {menu_type} menu: {e}", file=sys.stderr)
            return {}

    def parse_menu_items(self, data: dict, target_date: str) -> list[str]:
        """Extract menu item names for a specific date (deduplicated)."""
        items = []
        seen = set()
        for day in data.get("days", []):
            if day.get("date") == target_date:
                for item in day.get("menu_items", []):
                    if item.get("is_section_title"):
                        continue
                    food = item.get("food")
                    if food:
                        name = food.get("name")
                        if name and name not in seen:
                            seen.add(name)
                            items.append(name)
        return items

    def get_entrees_only(self, data: dict, target_date: str) -> list[str]:
        """Extract only entree items (main dishes) for a specific date.

        Items under sections with 'ENTREE' in the title are considered entrees.
        """
        items = []
        seen = set()
        for day in data.get("days", []):
            if day.get("date") == target_date:
                in_entree_section = False
                for item in day.get("menu_items", []):
                    if item.get("is_section_title"):
                        section_text = item.get("text", "").upper()
                        in_entree_section = "ENTREE" in section_text
                        continue
                    if in_entree_section:
                        food = item.get("food")
                        if food:
                            name = food.get("name")
                            if name and name not in seen:
                                seen.add(name)
                                items.append(name)
        return items

    def get_daily_menu(
        self,
        school: str,
        date: datetime,
        entrees_only: bool = False
    ) -> dict:
        """Get both breakfast and lunch menus for a specific date."""
        date_str = date.strftime("%Y-%m-%d")

        breakfast_data = self.fetch_menu(school, "breakfast", date)
        lunch_data = self.fetch_menu(school, "lunch", date)

        if entrees_only:
            breakfast_items = self.get_entrees_only(breakfast_data, date_str)
            lunch_items = self.get_entrees_only(lunch_data, date_str)
        else:
            breakfast_items = self.parse_menu_items(breakfast_data, date_str)
            lunch_items = self.parse_menu_items(lunch_data, date_str)

        return {
            "date": date_str,
            "day_of_week": date.strftime("%A"),
            "breakfast": breakfast_items,
            "lunch": lunch_items
        }


def format_menu_text(menu: dict) -> str:
    """Format menu data as readable text."""
    lines = [
        f"📅 {menu['day_of_week']}, {menu['date']}",
        ""
    ]

    if menu["breakfast"]:
        lines.append("🥣 Breakfast:")
        for item in menu["breakfast"]:
            lines.append(f"   • {item}")
    else:
        lines.append("🥣 Breakfast: No menu available")

    lines.append("")

    if menu["lunch"]:
        lines.append("🍽️  Lunch:")
        for item in menu["lunch"]:
            lines.append(f"   • {item}")
    else:
        lines.append("🍽️  Lunch: No menu available")

    return "\n".join(lines)


def format_menu_compact(menu: dict) -> str:
    """Format menu in a compact single-line format."""
    breakfast = ", ".join(menu["breakfast"][:3]) if menu["breakfast"] else "None"
    lunch = ", ".join(menu["lunch"][:3]) if menu["lunch"] else "None"

    if len(menu["breakfast"]) > 3:
        breakfast += f" (+{len(menu['breakfast']) - 3} more)"
    if len(menu["lunch"]) > 3:
        lunch += f" (+{len(menu['lunch']) - 3} more)"

    return f"{menu['day_of_week']}: 🥣 {breakfast} | 🍽️ {lunch}"


def list_schools(client: NutrisliceClient) -> None:
    """Print all available schools for the district."""
    schools = client.fetch_schools()
    if not schools:
        print(f"No schools found for district '{client.district}'", file=sys.stderr)
        print("Check that the district slug is correct.", file=sys.stderr)
        return

    print(f"Schools in '{client.district}' ({len(schools)} total):\n")

    # Group by type based on slug patterns
    high = []
    middle = []
    elementary = []
    other = []

    for school in sorted(schools, key=lambda s: s["name"]):
        slug = school["slug"]
        name = school["name"]
        entry = (slug, name)

        if "high-school" in slug:
            high.append(entry)
        elif "middle-school" in slug:
            middle.append(entry)
        elif "elementary" in slug:
            elementary.append(entry)
        else:
            other.append(entry)

    def print_section(title: str, items: list[tuple[str, str]]) -> None:
        if items:
            print(f"{title}:")
            for slug, name in items:
                print(f"  {slug:45} {name}")
            print()

    print_section("HIGH SCHOOLS", high)
    print_section("MIDDLE SCHOOLS", middle)
    print_section("ELEMENTARY SCHOOLS", elementary)
    print_section("OTHER", other)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch school lunch menus from Nutrislice",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -d mydistrict -l                  # List all schools in district
  %(prog)s -d mydistrict lincoln             # Today's menu for Lincoln Elementary
  %(prog)s -d mydistrict lincoln -t          # Tomorrow's menu
  %(prog)s -d mydistrict lincoln -w          # This week's menus
  %(prog)s -d mydistrict lincoln -e          # Only show main dishes
  %(prog)s -d mydistrict lincoln -j          # Output as JSON

Finding your district:
  District slugs are typically the district name without spaces (e.g., 'mydistrict').
  Check your school's Nutrislice menu URL to find the district slug.
        """
    )

    parser.add_argument(
        "school",
        nargs="?",
        help="School name or slug (partial matches work)"
    )

    parser.add_argument(
        "--district", "-d",
        required=True,
        help="District slug (found in your school's Nutrislice URL)"
    )

    parser.add_argument(
        "--list-schools", "-l",
        action="store_true",
        help="List all schools in the district"
    )

    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--date",
        type=str,
        help="Specific date (YYYY-MM-DD format)"
    )
    date_group.add_argument(
        "--tomorrow", "-t",
        action="store_true",
        help="Get tomorrow's menu"
    )
    date_group.add_argument(
        "--week", "-w",
        action="store_true",
        help="Get this week's menus (Mon-Fri)"
    )

    parser.add_argument(
        "--entrees", "-e",
        action="store_true",
        help="Only show entree items (main dishes)"
    )

    parser.add_argument(
        "--compact", "-c",
        action="store_true",
        help="Compact output format"
    )

    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show raw API response (for debugging)"
    )

    args = parser.parse_args()

    client = NutrisliceClient(args.district)

    # Handle --list-schools
    if args.list_schools:
        list_schools(client)
        return

    # Require school if not listing
    if not args.school:
        parser.error("school is required (or use --list-schools)")

    # Resolve school name
    school = client.resolve_school(args.school)
    if not school:
        print(f"Could not find school matching '{args.school}'", file=sys.stderr)
        print(f"Use --list-schools to see available schools in '{args.district}'", file=sys.stderr)
        sys.exit(1)

    # Determine target date(s)
    today = datetime.now()

    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
        dates = [target_date]
    elif args.tomorrow:
        dates = [today + timedelta(days=1)]
    elif args.week:
        monday = today - timedelta(days=today.weekday())
        dates = [monday + timedelta(days=i) for i in range(5)]
    else:
        dates = [today]

    if args.raw:
        for date in dates:
            print(f"\n=== Raw API Response for {date.strftime('%Y-%m-%d')} ===")
            lunch_data = client.fetch_menu(school, "lunch", date)
            print(json.dumps(lunch_data, indent=2))
        return

    menus = []
    for date in dates:
        menu = client.get_daily_menu(school, date, entrees_only=args.entrees)
        menus.append(menu)

    # Output
    if args.json:
        if len(menus) == 1:
            print(json.dumps(menus[0], indent=2))
        else:
            print(json.dumps(menus, indent=2))
    elif args.compact:
        for menu in menus:
            print(format_menu_compact(menu))
    else:
        for i, menu in enumerate(menus):
            if i > 0:
                print("\n" + "─" * 40 + "\n")
            print(format_menu_text(menu))


if __name__ == "__main__":
    main()
