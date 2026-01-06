# Nutrislice Menu CLI

Fetch school breakfast/lunch menus from any Nutrislice-powered school district.

## Installation

```bash
git clone https://github.com/brandonroeder/nutrislice-cli.git
cd nutrislice-cli
pip install .
```

## Usage

After installation, you'll have two commands available: `lunch` and `menu` (they're identical).

### Finding Your District

District slugs are typically the district name without spaces. To find yours, check your school's Nutrislice menu URL - it will look like:

```
https://{district}.nutrislice.com/...
```

The `{district}` part is what you need.

### List Schools in a District

```bash
lunch -d mydistrict --list-schools
lunch -d mydistrict -l
```

### Get Today's Menu

```bash
lunch -d mydistrict lincoln
```

Partial school names work - the CLI will match against available schools.

### More Options

```bash
# Tomorrow's menu
lunch -d mydistrict lincoln --tomorrow
lunch -d mydistrict lincoln -t

# This week's menus (Mon-Fri)
lunch -d mydistrict lincoln --week
lunch -d mydistrict lincoln -w

# Only show main dishes (entrees)
lunch -d mydistrict lincoln --entrees
lunch -d mydistrict lincoln -e

# Compact one-line format
lunch -d mydistrict lincoln --compact
lunch -d mydistrict lincoln -c

# JSON output
lunch -d mydistrict lincoln --json
lunch -d mydistrict lincoln -j

# Specific date
lunch -d mydistrict lincoln --date 2026-01-15

# Debug: show raw API response
lunch -d mydistrict lincoln --raw
```

## Example Output

```
$ lunch -d mydistrict lincoln

📅 Monday, 2026-01-06

🥣 Breakfast:
   • Mini Maple Waffles
   • Lucky Charms
   • Banana Muffin

🍽️  Lunch:
   • Chicken Nuggets
   • Cheese Pizza
   • PB&J Sandwich
```

```
$ lunch -d mydistrict lincoln --week --compact

Monday: 🥣 Mini Maple Waffles, Lucky Charms, Banana Muffin | 🍽️ Chicken Nuggets, Cheese Pizza, PB&J (+8 more)
Tuesday: 🥣 French Toast Sticks, Cocoa Puffs (+6 more) | 🍽️ Beef Tacos, Cheese Quesadilla (+10 more)
...
```

## API

This tool uses the public Nutrislice API:

```
https://{district}.api.nutrislice.com/menu/api/schools
https://{district}.api.nutrislice.com/menu/api/weeks/school/{school}/menu-type/{breakfast|lunch}/{year}/{month}/{day}/
```

## Disclaimer

This is an unofficial tool and is not affiliated with, endorsed by, or connected to Nutrislice. Menu data is fetched from Nutrislice's public API.

## License

MIT
