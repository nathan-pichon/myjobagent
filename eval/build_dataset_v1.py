"""Build a curated eval dataset v1 (hand-labelled ground truth).

Ground truth is authored deliberately against the DEFAULT profile
(`jobhunt.config.default_config()`): core stack Node.js/TypeScript, target
roles Senior Backend / Architect / Tech Lead / Principal / Fractional CTO,
geography Nice/Cannes/Sophia-Antipolis/Monaco/Remote-France, contracts
CDI/Freelance/Mission, seniority Senior.

`label` = "match" means a human says this offer is worth applying to for that
profile (the engine should score it >= threshold). Texts mimic real extracted
postings (FR/EN mix, some messy). Augment later with real scraped offers.

Run:  python -m eval.build_dataset_v1   ->  writes eval/dataset.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path

# (id, label, human_score|None, note, text)
ROWS = [
    # ---------------- clear MATCHES ----------------
    ("m01", "match", 92, "senior backend node/ts nice cdi", """
Senior Backend Engineer (H/F) — CDI — Nice (Sophia-Antipolis) ou télétravail.
Rejoignez notre équipe produit pour concevoir des APIs robustes et scalables.
Stack : Node.js, TypeScript, NestJS, PostgreSQL, Docker, AWS. Vous avez 6+ ans
d'expérience backend, une solide culture des architectures distribuées et du
testing. Missions : conception d'APIs REST/GraphQL, revue de code, mentorat des
développeurs juniors. Contrat CDI, rémunération 60-80k€ selon expérience.
Bureaux à Nice, télétravail hybride 3j/semaine possible."""),

    ("m02", "match", 90, "tech lead node remote france freelance", """
Mission Freelance — Tech Lead Backend Node.js / TypeScript — Full Remote (France).
Pour un éditeur SaaS en forte croissance, nous cherchons un Tech Lead backend
pour piloter une équipe de 4 développeurs. Environnement : Node.js, TypeScript,
MongoDB, Kubernetes, GCP. TJM 600-750€. Démarrage ASAP, mission longue (12 mois
renouvelable). 100% télétravail depuis la France. Vous définissez les standards
techniques et participez aux choix d'architecture."""),

    ("m03", "match", 88, "backend node mongo sophia cdi", """
Backend Developer — Node.js — Sophia-Antipolis — CDI
Notre scale-up recrute un développeur backend senior pour renforcer son équipe.
Technologies : Node.js, TypeScript, Express, MongoDB Atlas, Redis, Docker.
Vous concevez et maintenez des microservices à fort trafic. 5 ans d'XP minimum.
Localisation : Sophia-Antipolis, hybride. CDI, 55-70k€ + BSPCE."""),

    ("m04", "match", 82, "backend ts nestjs remote europe cdi", """
Senior Backend Engineer — TypeScript / NestJS — Remote (Europe, France-friendly)
We are a remote-first company hiring across Europe. Our stack: TypeScript,
NestJS, Node.js, PostgreSQL, Kafka, Kubernetes. You will own backend services
end to end. 7+ years experience. Permanent contract (CDI equivalent), salary
70-90k€. Fully remote — you can work from anywhere in the EU including France."""),

    ("m05", "match", 80, "freelance mission backend node remote fr", """
Mission — Développeur Backend Node.js — Remote France — 6 mois
ESN recherche pour son client (fintech) un développeur backend confirmé.
Stack : Node.js, TypeScript, AWS Lambda, DynamoDB. Vous intervenez sur des
APIs de paiement. Télétravail total depuis la France. Freelance, TJM 550€."""),

    ("m06", "match", 85, "principal engineer node ts cannes hybrid", """
Principal Engineer — Node.js & TypeScript — Cannes (hybride)
Join our engineering leadership. You will shape the architecture of our
event-driven platform (Node.js, TypeScript, RabbitMQ, Docker, Kubernetes).
10+ years, strong system design. Based in Cannes, 2 days remote per week. CDI."""),

    ("m07", "match", 72, "fullstack strong backend node remote france cdi", """
Senior Full-Stack Engineer (backend-leaning) — Node.js / React — Remote France
You'll spend ~70% of your time on the backend: Node.js, TypeScript, Prisma,
PostgreSQL; plus some React on the frontend. Remote within France, CDI, 60-75k€.
We value strong API design and ownership."""),

    ("m08", "match", 90, "backend architect node k8s nice", """
Backend Architect — Node.js / Kubernetes — Nice
We are hiring a backend architect to lead the redesign of our core platform.
Deep expertise in Node.js, TypeScript, microservices, Kubernetes, and cloud
(AWS/GCP) required. On-site in Nice with flexible remote. Permanent role, senior."""),

    ("m09", "match", 78, "lead backend node monaco hybrid", """
Lead Développeur Backend — Node.js / TypeScript — Monaco (hybride)
Au sein d'une équipe de 6 ingénieurs, vous encadrez le développement backend.
Stack Node.js, TypeScript, MongoDB, Docker. Monaco, hybride. CDI, package
attractif. Expérience senior exigée (7+ ans)."""),

    ("m10", "match", 70, "fractional cto node remote france", """
Fractional CTO / Tech Advisor — Remote France — Freelance
Early-stage startup seeks a fractional CTO 2-3 days/week. You guide technical
strategy and hands-on architecture. Our stack is Node.js + TypeScript. Remote
from France. Freelance engagement, day rate negotiable."""),

    # ---------------- borderline, judged MATCH ----------------
    ("b01", "match", None, "mid backend node ts nice cdi (mid not senior)", """
Développeur Backend Node.js / TypeScript — Nice — CDI
Nous cherchons un développeur backend (niveau intermédiaire à confirmé) pour
notre plateforme. Stack : Node.js, TypeScript, PostgreSQL, Docker. Nice,
télétravail partiel. CDI 45-58k€. 3 ans d'expérience minimum."""),

    ("b02", "match", None, "backend node remote eu company unspecified country", """
Backend Engineer — Node.js / TypeScript — Remote
European B2B company. Stack: Node.js, TypeScript, GraphQL, PostgreSQL, AWS.
Remote position (no specific country stated). Permanent contract. We hire across
the EU. 5+ years backend experience."""),

    # ---------------- clear NO-MATCH ----------------
    ("n01", "no_match", 15, "java spring paris onsite", """
Ingénieur Backend Java / Spring Boot — Paris (sur site) — CDI
Grand groupe bancaire recherche un ingénieur backend Java. Stack : Java 17,
Spring Boot, Hibernate, Oracle. Présentiel à Paris La Défense, 5j/semaine.
8 ans d'XP. Pas de télétravail."""),

    ("n02", "no_match", 10, "php symfony lyon (excluded stack)", """
Développeur PHP / Symfony — Lyon — CDI
Agence web recrute un développeur backend PHP. Symfony, MySQL, Doctrine.
Sur site à Lyon. 4 ans d'expérience. CDI 38-45k€."""),

    ("n03", "no_match", 25, "junior node nice", """
Développeur Junior Node.js — Nice — CDI
Premier emploi ? Rejoignez-nous ! Vous apprendrez Node.js, Express et MongoDB
auprès de développeurs seniors. Diplôme bac+5 ou bootcamp. 0-2 ans. Nice.
Formation assurée. CDI 32-38k€."""),

    ("n04", "no_match", 20, "frontend react senior remote", """
Senior Frontend Engineer — React / Next.js — Remote France
We need a frontend specialist. Stack: React, Next.js, TypeScript, Tailwind.
You build delightful UIs. No backend responsibilities. Remote France, CDI."""),

    ("n05", "no_match", 10, "data scientist python ml paris", """
Data Scientist — Python / Machine Learning — Paris
Join our data team. Python, pandas, scikit-learn, PyTorch, SQL. You build ML
models and dashboards. Paris, hybrid. PhD or MSc preferred. CDI."""),

    ("n06", "no_match", 15, "dotnet csharp backend toulouse", """
Développeur Backend .NET / C# — Toulouse — CDI
Stack : C#, .NET 8, ASP.NET Core, SQL Server, Azure. Aérospatial. Sur site
à Toulouse. 6 ans d'expérience. CDI."""),

    ("n07", "no_match", 20, "backend node remote US-only location fail", """
Backend Engineer — Node.js / TypeScript — Remote (US only)
Great stack (Node.js, TypeScript, PostgreSQL) but this is a US-based role.
You must reside in the United States and be authorized to work in the US.
Remote within the US only. Full-time."""),

    ("n08", "no_match", 5, "blog article not a job", """
10 bonnes pratiques pour écrire des APIs Node.js performantes en 2026
Dans cet article de blog, nous partageons nos conseils pour optimiser vos
applications Node.js : mise en cache, pagination, gestion des erreurs, et plus.
Abonnez-vous à notre newsletter pour ne rien manquer ! Catégorie : Tutoriels."""),

    ("n09", "no_match", 5, "pricing/about page not a job", """
Nos tarifs — Plans et abonnements
Découvrez nos offres : Starter à 9€/mois, Pro à 29€/mois, Entreprise sur devis.
Tous nos plans incluent le support. Essai gratuit de 14 jours. À propos de
nous : fondée en 2018, notre mission est de simplifier le recrutement."""),

    ("n10", "no_match", 12, "ruby rails berlin onsite", """
Senior Backend Engineer — Ruby on Rails — Berlin (on-site)
Stack: Ruby, Rails, PostgreSQL, Sidekiq. On-site in Berlin, relocation
package available. 6+ years. Must relocate to Germany. Permanent."""),

    ("n11", "no_match", 18, "internship backend node nice", """
Stage — Développeur Backend Node.js — Nice — 6 mois
Stage de fin d'études. Vous découvrirez Node.js et MongoDB. Convention de
stage obligatoire. Gratification légale. Nice. Étudiant bac+5."""),

    ("n12", "no_match", 30, "go backend senior paris (stack not core)", """
Senior Backend Engineer — Go (Golang) — Paris — CDI
We build high-performance services in Go. Stack: Go, gRPC, PostgreSQL,
Kubernetes. On-site Paris with 1 day remote. 6+ years in Go. CDI."""),

    ("n13", "no_match", 5, "sales account manager unrelated", """
Account Manager — SaaS B2B — Lyon
Vous gérez un portefeuille de clients grands comptes, négociez les
renouvellements et développez l'upsell. Profil commercial, 3 ans en vente B2B.
Lyon, déplacements fréquents. CDI + variable."""),

    # ---------------- borderline, judged NO-MATCH ----------------
    ("b03", "no_match", None, "python django senior remote france (core stack mismatch)", """
Senior Backend Engineer — Python / Django — Full Remote France
Strong remote-France role with great conditions (CDI, 65-80k€). Stack: Python,
Django, DRF, PostgreSQL, Celery, Docker. 7+ years. Fully remote from France.
No Node.js or TypeScript involved."""),

    ("b04", "no_match", None, "backend node senior bordeaux onsite (loc fail)", """
Senior Backend Engineer — Node.js / TypeScript — Bordeaux (sur site)
Perfect stack match (Node.js, TypeScript, PostgreSQL, Docker) but the role is
strictly on-site in Bordeaux, no remote option. 6 years experience. CDI."""),
]


def main() -> None:
    out = Path("eval/dataset.jsonl")
    with out.open("w", encoding="utf-8") as f:
        for _id, label, human, note, text in ROWS:
            row = {
                "id": _id,
                "text": " ".join(text.split()),  # collapse whitespace like extracted text
                "label": label,
                "human_score": human,
                "note": note,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n_match = sum(1 for r in ROWS if r[1] == "match")
    print(f"Wrote {len(ROWS)} rows to {out} ({n_match} match / {len(ROWS)-n_match} no_match)")


if __name__ == "__main__":
    main()
