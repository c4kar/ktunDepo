import json
from collections import defaultdict

with open('dersProgrami.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

courses = set()
for r, clist in d.items():
    for c in clist:
        courses.add((c['donem'], c['ders_adi']))

for donem, ad in sorted(courses, key=lambda x: (x[0], x[1])):
    print(f"{donem} - {ad}")
