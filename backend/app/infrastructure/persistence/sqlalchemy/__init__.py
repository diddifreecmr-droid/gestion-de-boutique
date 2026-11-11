"""Adaptateur SQL des ports de persistance (SQLAlchemy 2 Core, confiné à ce paquet — D3).

Aucun SQL propre à un moteur : seules des constructions SQLAlchemy portables (requêtes
paramétrées, contraintes `UNIQUE`/`CHECK`, savepoints). La seule hypothèse sur la base est une
isolation « lecture validée » avec verrous de ligne en écriture (PostgreSQL, MySQL/InnoDB,
SQL Server, Oracle ; SQLite verrouille la base entière, ce qui reste correct).
"""
