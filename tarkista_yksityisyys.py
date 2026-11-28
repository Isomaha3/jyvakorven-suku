#!/usr/bin/env python3
"""Julkisen version yksityisyystarkistus.

Varmistaa, ettei index.html:n DATA-objekti paljasta elossa olevien tietoja:
1. Elossa olevalla (living: true) saa olla vain sallitut kentät, ei nimeä,
   syntymäaikaa, paikkaa, kuvaa eikä omaa muistiinpanoa.
2. Perheessä, jonka kaikki puolisot ovat elossa, ei saa olla vihkimisaikaa,
   vihkipaikkaa eikä lähdetietoa.
3. Henkilö, jolla ei ole kuolintietoja ja joka on syntynyt alle 100 vuotta
   sitten, mutta jota ei ole merkitty elossa olevaksi, nostetaan esiin.

Ei muuta mitään. Paluukoodi 1, jos löytyy vuoto (kohdat 1 ja 2).
Käyttö:  python3 tarkista_yksityisyys.py [index.html]
"""
import datetime
import json
import sys

TIEDOSTO = sys.argv[1] if len(sys.argv) > 1 else "index.html"
SALLITUT = {"id", "given", "surname", "sex", "famc", "fams", "dead", "living", "note"}
PIILOTETTU_NIMI = "Elävä henkilö"
PIILOTETTU_HUOMIO = "Elossa olevan henkilön tiedot on piilotettu sivun julkisesta versiosta."
PERHEEN_TIEDOT = ("marr", "marriage", "marrPlace", "src")


def lue_data(polku):
    html = open(polku, encoding="utf-8").read()
    alku = html.index("const DATA = ") + len("const DATA = ")
    data, _ = json.JSONDecoder().raw_decode(html[alku:])
    return data


def main():
    d = lue_data(TIEDOSTO)
    P, F = d["people"], d["families"]
    elossa = {i for i, p in P.items() if p.get("living")}
    vuodot, huomiot = [], []

    for i in sorted(elossa):
        p = P[i]
        ylimaaraiset = sorted(k for k, v in p.items() if k not in SALLITUT and v not in (None, "", [], False))
        if ylimaaraiset:
            vuodot.append(f"ELÄVÄ {i}: ylimääräiset kentät {', '.join(ylimaaraiset)}")
        if p.get("given") != PIILOTETTU_NIMI or p.get("surname"):
            vuodot.append(f"ELÄVÄ {i}: nimi näkyy ({p.get('given')} {p.get('surname')})")
        if p.get("note") not in (None, "", PIILOTETTU_HUOMIO):
            vuodot.append(f"ELÄVÄ {i}: oma muistiinpano näkyy")

    for fid, f in sorted(F.items()):
        puolisot = [x for x in (f.get("husb"), f.get("wife")) if x]
        if puolisot and all(x in elossa for x in puolisot):
            nakyvat = [k for k in PERHEEN_TIEDOT if f.get(k)]
            if nakyvat:
                vuodot.append(f"PERHE {fid}: elossa olevien perheessä näkyy {', '.join(f'{k}={f[k]}' for k in nakyvat)}")

    raja = datetime.date.today().year - 100
    for i, p in sorted(P.items()):
        if i in elossa:
            continue
        kuollut = p.get("death") or p.get("deathYear") or p.get("deathPlace")
        if not kuollut and (p.get("birthYear") or 0) > raja:
            huomiot.append(f"TARKISTA {i}: {p.get('given')} {p.get('surname')} s. {p.get('birthYear')}, ei kuolintietoja eikä piilotettu")

    print(f"Henkilöitä {len(P)}, elossa olevia {len(elossa)}, perheitä {len(F)}")
    print(f"Vuotoja: {len(vuodot)}")
    for r in vuodot:
        print("  " + r)
    print(f"Tarkistettavia: {len(huomiot)}")
    for r in huomiot:
        print("  " + r)
    return 1 if vuodot else 0


if __name__ == "__main__":
    sys.exit(main())
