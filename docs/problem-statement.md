# Problem Statement

## Background

Policing data in India is generated at the police-station level: FIRs are registered at a station, emergency calls arrive through Dial-100, and cyber/narcotics-related complaints come in through the 1930 helpline. Oversight and resourcing decisions, however, are made at district and state level.

## The Problem

Crime data is recorded at police-station level but managed across districts and states, with no unified view. The same event can appear as a Dial-100 call and, hours later, as an FIR. Category names differ between sources, addresses are free text, and spreadsheets arrive with inconsistent headers. As a result:

- No single, de-duplicated picture of *how often* each kind of crime occurs, *where*, and whether it is rising.
- Hotspots that never generated a police record (a corner where drugs are sold, a stretch of road where hit-and-runs keep happening) are invisible until they become incidents.
- Turning numbers into a decision (where should patrols go this week? which district needs attention this month?) is manual, slow and inconsistent.

## Who is Affected

- **Station House Officers and beat supervisors**, who decide where to redeploy patrols week to week.
- **District and state-level commanders**, who need a comparable view across stations and districts.
- **Citizens** in under-reported areas, who currently have no safe, anonymous way to flag activity.

## Why It Matters

Enforcement that depends on already-registered incidents is reactive by construction. Every day a hotspot goes unseen is a day it can grow; every duplicated or mis-categorised record distorts the count that resources are allocated by.

## Why Existing Solutions Fall Short

Station-level records systems are not designed for cross-source, cross-district aggregation, and generic dashboards show whatever is in the table — including duplicates and unmappable rows. Opaque "risk scores" are hard for an officer to trust or justify. SafeGrid instead counts raw, de-duplicated frequency by category, shows the trend, admits anonymous tips, and explains every score in plain language.
