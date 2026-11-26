#!/usr/bin/env python3
"""Sukutietojen johdonmukaisuustarkistus.

Lukee index.html:n DATA-objektin ja tulostaa löydökset. Ei muuta mitään.
Käyttö:  python3 tarkista_tiedot.py [index.html]
Paluukoodi 1, jos löytyy viittausvirheitä (rikkinäisiä perhe- tai henkilöviitteitä).
"""
import json
import re
import sys
from collections import defaultdict

TIEDOSTO = sys.argv[1] if len(sys.argv) > 1 else "index.html"


def lue_data(polku):
    html = open(polku, encoding="utf-8").read()
    alku = html.index("const DATA = ") + len("const DATA = ")
    data, _ = json.JSONDecoder().raw_decode(html[alku:])
    return data


def lue_tarinat(polku):
    """Sivun näkyvä teksti ennen DATA-objektia, HTML-tagit poistettuna."""
    html = open(polku, encoding="utf-8").read()
    teksti = html[: html.index("const DATA = ")]
    return re.sub(r"<[^>]+>", " ", teksti)


def tarkka_syntyma(p):
    """True, jos syntymä on tarkka päivämäärä eikä arvio (n. 1724)."""
    return bool(re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}", str(p.get("birth") or "").strip()))


def ika_huomiot(P, nimi):
    """Vertaa muistiinpanojen ikämainintoja syntymävuoteen.

    'täytti 70 vuotta ... 27.2.1922' -> syntymävuoden pitäisi olla 1852.
    'kuoli ... 76-vuotiaana' -> syntymävuosi kuolinvuosi-76 tai -77, yhden vuoden
    heitolla (haudattujen iät ovat kirkonkirjoissa usein epätarkkoja).
    Vain tarkat syntymäpäivät tarkistetaan; arviot (n. 1724) ohitetaan.
    """
    out = []
    for pid, p in P.items():
        sv, kv, note = p.get("birthYear"), p.get("deathYear"), p.get("note") or ""
        if not sv or not tarkka_syntyma(p):
            continue
        for lause in re.split(r"(?<=[.;])\s+(?=[A-ZÅÄÖ])", note):
            m = re.search(r"[Tt]äytti (\d{1,3}) vuotta", lause)
            if m:
                y = re.findall(r"\b(1[6-9]\d\d|20\d\d)\b", lause[m.end():])
                if y and int(y[0]) - int(m.group(1)) != sv:
                    out.append(f"IKÄ/TEKSTI: {nimi(pid)} s. {p['birth']}, mutta muistiinpanossa "
                               f"'täytti {m.group(1)} vuotta' vuonna {y[0]} (-> s. {int(y[0]) - int(m.group(1))})")
            m = re.search(r"(\d{1,3})-vuotiaana", lause)
            if m and kv and "kuoli" in lause.lower():
                ika = int(m.group(1))
                # Haudattujen ikä on kirjoissa usein vuoden pielessä, joten
                # sallitaan yhden vuoden heitto laskennallisesta iästä.
                if not kv - ika - 2 <= sv <= kv - ika + 1:
                    out.append(f"IKÄ/TEKSTI: {nimi(pid)} s. {sv}, k. {kv}, mutta muistiinpanossa {ika}-vuotiaana")
    return out


def tarina_huomiot(P, tarinat, nimi):
    """Etsii tarinoista muodot 'Josef (1852–1925)' ja vertaa niitä tietoihin.

    Henkilö katsotaan samaksi, kun etunimi täsmää ja toinen vuosista täsmää.
    Silloin toisen vuoden ero on todennäköinen ristiriita.
    """
    out = []
    for m in re.finditer(r"([A-ZÅÄÖ][a-zåäö]+) \((1\d{3})[–-](1\d{3})\)", tarinat):
        etu, s, k = m.group(1), int(m.group(2)), int(m.group(3))
        for pid, p in P.items():
            nimet = re.findall(r"[A-ZÅÄÖ][a-zåäö]+", p.get("given", ""))
            if etu not in nimet:
                continue
            sv, kv = p.get("birthYear"), p.get("deathYear")
            if sv == s and kv and kv != k:
                out.append(f"TARINA: '{m.group(0)}', mutta {nimi(pid)} k. {kv}")
            elif kv == k and sv and sv != s:
                out.append(f"TARINA: '{m.group(0)}', mutta {nimi(pid)} s. {p.get('birth') or sv}")
    return out


def vuosi(teksti):
    """Ensimmäinen nelinumeroinen vuosi (vaihteluvälissä 'n. 1560–1580' alaraja)."""
    if not teksti:
        return None
    m = re.search(r"(1[5-9]\d\d|20\d\d)", str(teksti))
    return int(m.group(1)) if m else None


def main():
    d = lue_data(TIEDOSTO)
    P, F = d["people"], d["families"]
    nimi = lambda i: f"{P[i]['given']} {P[i]['surname']} ({i})"
    viite, muut = [], []

    if d.get("root") not in P:
        viite.append(f"Juurihenkilö {d.get('root')} puuttuu")

    for fid, f in F.items():
        for r in [f.get("husb"), f.get("wife")] + f.get("children", []):
            if r and r not in P:
                viite.append(f"Perhe {fid} viittaa puuttuvaan henkilöön {r}")
        for c in f.get("children", []):
            if c in P and fid not in P[c]["famc"]:
                viite.append(f"{nimi(c)} on perheen {fid} lapsi, mutta famc ei sisällä perhettä")
        for rooli in ("husb", "wife"):
            r = f.get(rooli)
            if r in P and fid not in P[r]["fams"]:
                viite.append(f"{nimi(r)} on perheen {fid} puoliso, mutta fams ei sisällä perhettä")
    for pid, p in P.items():
        for fid in p["famc"]:
            if fid not in F:
                viite.append(f"{nimi(pid)}: vanhempien perhe {fid} puuttuu")
            elif pid not in F[fid].get("children", []):
                viite.append(f"{nimi(pid)}: perhe {fid} ei listaa häntä lapseksi")
        for fid in p["fams"]:
            if fid not in F:
                viite.append(f"{nimi(pid)}: oma perhe {fid} puuttuu")
            elif pid not in (F[fid].get("husb"), F[fid].get("wife")):
                viite.append(f"{nimi(pid)}: perhe {fid} ei listaa häntä puolisoksi")

    for pid, p in P.items():
        sv, kv = p.get("birthYear"), p.get("deathYear")
        if p.get("birth") and sv and vuosi(p["birth"]) != sv:
            muut.append(f"VUOSI: {nimi(pid)} birth '{p['birth']}', mutta birthYear {sv}")
        if p.get("death") and kv and vuosi(p["death"]) != kv:
            muut.append(f"VUOSI: {nimi(pid)} death '{p['death']}', mutta deathYear {kv}")
        if sv and kv and kv < sv:
            muut.append(f"IKÄ: {nimi(pid)} kuoli ({kv}) ennen syntymää ({sv})")
        if sv and kv and kv - sv > 105:
            muut.append(f"IKÄ: {nimi(pid)} elinikä {kv - sv} v")
        if p.get("living") and (kv or p.get("death")):
            muut.append(f"ELOSSA: {nimi(pid)} merkitty eläväksi, mutta kuolintieto on")
        if not p.get("living") and sv and sv > 1935 and not p.get("dead"):
            muut.append(f"ELOSSA?: {nimi(pid)} s. {sv}, ei kuolintietoa eikä living-merkintää")

    for fid, f in F.items():
        for c in f.get("children", []):
            cv = P.get(c, {}).get("birthYear")
            if not cv:
                continue
            for rooli, ala, yla in (("husb", 15, 75), ("wife", 14, 50)):
                r = f.get(rooli)
                if r not in P:
                    continue
                pv, pk = P[r].get("birthYear"), P[r].get("deathYear")
                if pv and not ala <= cv - pv <= yla:
                    muut.append(f"IKÄ: {nimi(r)} (s. {pv}) oli {cv - pv} v lapsen {nimi(c)} syntyessä ({cv})")
                if pk and ((rooli == "wife" and cv > pk) or (rooli == "husb" and cv > pk + 1)):
                    muut.append(f"IKÄ: {nimi(r)} kuoli {pk}, lapsi {nimi(c)} s. {cv}")
        h, w = f.get("husb"), f.get("wife")
        if h in P and P[h]["sex"] == "F":
            muut.append(f"SUKUPUOLI: perheen {fid} isä {nimi(h)} on merkitty naiseksi")
        if w in P and P[w]["sex"] == "M":
            muut.append(f"SUKUPUOLI: perheen {fid} äiti {nimi(w)} on merkitty mieheksi")

    muut += ika_huomiot(P, nimi)
    muut += tarina_huomiot(P, lue_tarinat(TIEDOSTO), nimi)

    ryhmat = defaultdict(list)
    for pid, p in P.items():
        if p.get("birthYear") and not p.get("living"):
            ryhmat[(p["given"].split()[0], p["surname"], p["birthYear"])].append(pid)
    for k, v in ryhmat.items():
        if len(v) > 1:
            muut.append(f"TUPLA?: {k[0]} {k[1]} s. {k[2]}: {', '.join(v)}")

    print(f"Henkilöitä {len(P)}, perheitä {len(F)}")
    print(f"Viittausvirheitä: {len(viite)}")
    for r in viite:
        print("  " + r)
    print(f"Muita huomioita: {len(muut)}")
    for r in muut:
        print("  " + r)
    return 1 if viite else 0


if __name__ == "__main__":
    sys.exit(main())
