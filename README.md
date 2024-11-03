# 🧑‍🎓 StudFlaw

Looks up people by their 🇫🇷 French diploma records on `linternaute.com`.

- 🚀 **Multi-threaded** for high-speed execution
- 🔍 **Birthdate retrieval** for individuals who attempted but did not obtain a diploma, taking advantage of a design flaw on linternaute.com
- 📁 **JSON Export** support
- 📜 **Comprehensive Results** across all academies, graduation years, and diploma types

## 💻 Installation & usage
```
pip install studflaw
studflaw -n [First name | Last name | Both]
```
Parameters:
- -n | --name : Name of the target
- -s | --start (optional) : Start searching from the specified year (minimal and default value: 2007)
- -e | --end (optional) : End the search at the specified year (default value: current year)
- --json : Prints the result as a JSON array
- --threads : Select a custom number of threads (default: 2)

⚠️ Making a huge number of requests in a short amount of time might get you rate-limited.
Try setting the number of threads to 1 if you're about to search a generic name.

## 🎓 Supported diploma
- Brevet
- Bac
- BTS

The search covers records from 2007 to the current year. 
Note that not everyone will appear, as it depends on whether they allowed their results to be made public.

You may also *opt out of the results* by sending an email to `support@linternaute.zendesk.com`.

Template email (tested & approved):
```
Bonjour,

Je me permets de vous contacter concernant la présence de mes informations personnelles sur votre site. Je souhaite faire supprimer mes résultats au (diplôme + année) accessibles à cette adresse : (lien vers la page contenant les données).

Merci de bien vouloir retirer mon identité de votre base de données et de me confirmer par retour d'email que cette suppression a été effectuée.

Je vous remercie par avance pour votre compréhension et votre diligence.

Cordialement,
(Prénom Nom)
```

## 🔎 Difference from a manual search
When looking up someone on `linternaute.com`, you need to specify which diploma, which year and which academy you're looking for.
This tool covers all 3 of these cases, so you can input a first name / last name or both and you'll get results from any of these.
It also offers the possibility of *cracking a birthdate*, which you normally require to view someone's result, given that this person failed to obtain a diploma.
