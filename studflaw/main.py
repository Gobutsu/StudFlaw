import argparse
import json
import re
from datetime import datetime
from rich import print
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
import asyncio
import aiohttp

TYPES = ['brevet', 'bac', 'bts']

ACADEMIE_DICT = {
    "academie-aix-marseille": "Aix-Marseille",
    "academie-amiens": "Amiens",
    "academie-besancon": "Besançon",
    "academie-bordeaux": "Bordeaux",
    "academie-clermont-ferrand": "Clermont-Ferrand",
    "academie-corse": "Corse",
    "academie-creteil": "Créteil",
    "academie-dijon": "Dijon",
    "academie-grenoble": "Grenoble",
    "academie-guadeloupe": "Guadeloupe",
    "academie-guyane": "Guyane",
    "academie-la-reunion": "La Réunion",
    "academie-lille": "Lille",
    "academie-limoges": "Limoges",
    "academie-lyon": "Lyon",
    "academie-martinique": "Martinique",
    "academie-mayotte": "Mayotte",
    "academie-montpellier": "Montpellier",
    "academie-nancy-metz": "Nancy-Metz",
    "academie-nantes": "Nantes",
    "academie-nice": "Nice",
    "academie-normandie": "Normandie",
    "academie-nouvelle-caledonie": "Nouvelle-Calédonie",
    "academie-orleans-tours": "Orléans-Tours",
    "academie-paris": "Paris",
    "academie-poitiers": "Poitiers",
    "academie-polynesie-francaise": "Polynésie Française",
    "academie-reims": "Reims",
    "academie-rennes": "Rennes",
    "academie-saint-pierre-et-miquelon": "Saint-Pierre-et-Miquelon",
    "academie-strasbourg": "Strasbourg",
    "academie-toulouse": "Toulouse",
    "academie-versailles": "Versailles",
    "academie-wallis-et-futuna": "Wallis-et-Futuna"
}

BIRTHDAY_INDEX = [3, 1, 9, 2, 8, 0, 6, 4, 7, 5]

console = Console(stderr=True)

def get_academy_name(link):
    """Extract the academy name from the candidate's link."""
    academie_key = link.split("/")[1]
    return ACADEMIE_DICT.get(academie_key, academie_key)

async def fetch_candidates(session, diploma_type, year, page, input_name, semaphore):
    """Fetch candidates from the API."""
    url = f'https://search-candidate.linternaute.com/{diploma_type}/{year}/{page}?candidate-name={input_name}'
    try:
        async with semaphore:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                candidates = data.get('candidates', [])
                return candidates
    except aiohttp.ClientError as e:
        console.print(f"[bold red]Network error:[/bold red] {e}")
    except json.JSONDecodeError:
        console.print("[bold yellow]Warning:[/bold yellow] Could not decode JSON response.")
    return []

async def fetch_mention(session, diploma_type, candidate_id, semaphore):
    """Fetch the mention for a candidate. Returns [mention, birthdate]."""
    url = f"https://resultat-{diploma_type}.linternaute.com/candidat-{candidate_id}?xhr"
    try:
        async with semaphore:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                data = str(json.loads(json.loads(content))[0])
                html = data.replace("&quot;", "\"")
                mention_match = re.search(r'Résultat : (.+?)<', html)

                if mention_match:
                    return [mention_match.group(1), None]
                else:
                    match = re.search(r'data-birthdate="(\d+)"', html)
                    if not match:
                        return ["Refusé", None]
                    data_birthdate = match.group(1)

                    reordered_digits = [str(BIRTHDAY_INDEX.index(int(digit))) for digit in data_birthdate]

                    formatted_date = "".join(reordered_digits)
                    formatted_date = re.sub(r"(\d{2})(\d{2})(\d{4})", r"\1/\2/\3", formatted_date)

                    return ["Refusé", formatted_date]
    except aiohttp.ClientError as e:
        console.print(f"[bold red]Network error:[/bold red] {e}")
        return ["Error", None]

def create_candidate_entry(candidate, diploma_type, year):
    """Create a dictionary with candidate information."""
    candidate_id = str(candidate.get('id', 'N/A'))
    return {
        "diploma": diploma_type,
        "name": candidate.get('name', 'N/A'),
        "city": candidate.get('cityLabel', 'N/A'),
        "diplomaSerieLabel": candidate.get('diplomaSerieLabel', 'N/A'),
        "year": year,
        "academy": get_academy_name(candidate.get('link', 'N/A')),
        "mention": candidate.get('mention', 'N/A'),
        "birthdate": candidate.get('birthdate', 'N/A'),
        "id": candidate_id
    }

async def search_candidates(session, diploma_type, year, name, semaphore, seen_ids, lock, progress=None, task_id=None):
    """Search for candidates and return the entries and hits."""
    page = 0
    hits = 0
    entries = []
    while True:
        candidates = await fetch_candidates(session, diploma_type, year, page, name, semaphore)
        if not candidates:
            break

        mention_tasks = []
        valid_candidates = []
        for candidate in candidates:
            candidate_id = candidate.get('id')
            if candidate_id is None:
                continue
            candidate_id = str(candidate_id)
            candidate_key = (candidate_id, diploma_type, year)
            async with lock:
                if candidate_key in seen_ids:
                    continue
                seen_ids.add(candidate_key)
            valid_candidates.append(candidate)
            mention_tasks.append(
                asyncio.create_task(
                    fetch_mention(session, diploma_type, candidate_id, semaphore)
                )
            )

        mentions = await asyncio.gather(*mention_tasks, return_exceptions=True)
        for candidate, mention in zip(valid_candidates, mentions):
            if isinstance(mention, Exception):
                console.print(f"[bold red]Error fetching mention for candidate {candidate.get('id')}: {mention}[/bold red]")
                candidate['mention'] = 'Error'
                candidate['birthdate'] = None
            else:
                candidate['mention'] = mention[0]
                candidate['birthdate'] = mention[1]
            entry = create_candidate_entry(candidate, diploma_type, year)
            entries.append(entry)
        hits += len(valid_candidates)
        page += 1
    if progress and task_id is not None:
        progress.update(task_id, advance=1)
    return hits, entries

async def run_search(args):
    """Asynchronous function to perform the search."""
    output_data = []

    progress = Progress(console=console)
    task_id = progress.add_task("Searching...", total=len(TYPES) * (args.end - args.start + 1))
    progress.start()

    tasks = []
    for diploma_type in TYPES:
        for year in range(args.start, args.end + 1):
            tasks.append((diploma_type, year))

    semaphore = asyncio.Semaphore(args.threads)
    seen_ids = set()
    lock = asyncio.Lock()

    async with aiohttp.ClientSession() as session:
        search_tasks = [
            asyncio.create_task(
                search_candidates(session, diploma_type, year, args.name, semaphore, seen_ids, lock, progress, task_id)
            )
            for diploma_type, year in tasks
        ]

        total_hits = 0
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                console.print(f"[bold red]Error: {result}[/bold red]")
            else:
                hits, entries = result
                total_hits += hits
                output_data.extend(entries)

    progress.stop()

    if args.json:
        print(json.dumps(output_data, ensure_ascii=False, indent=4))
    else:
        table = Table(title="Candidate Search Results")
        table.add_column("Year", justify="right", style="yellow")
        table.add_column("Diploma", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("City", style="magenta")
        table.add_column("Academy", style="red")
        table.add_column("Birthdate", style="cyan")
        table.add_column("Diploma Label", style="blue")
        table.add_column("Mention", style="purple")

        for entry in output_data:
            row = [
                str(entry["year"]),
                entry["diploma"],
                entry["name"],
                entry["city"],
                entry["academy"],
                entry["birthdate"],
                entry["diplomaSerieLabel"],
                entry["mention"],
            ]
            table.add_row(*row)
        console.print(table)

    console.print(f"\nTotal Results: {len(output_data)}")

def main():
    """Main function to parse arguments and initiate the search."""
    parser = argparse.ArgumentParser(description="Fetch candidate information.")
    parser.add_argument("-n", "--name", required=True, help="Name of the candidate to search for")
    parser.add_argument("-s", "--start", type=int, default=2007, help="Start year for search")
    parser.add_argument("-e", "--end", type=int, default=datetime.now().year, help="End year for search")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--threads", type=int, default=2, help="Number of concurrent requests")
    args = parser.parse_args()

    asyncio.run(run_search(args))

if __name__ == '__main__':
    main()
