# joseph-api

Shared data model and API for the joseph-* family. Bottom of the dependency DAG: this package
imports nothing from other joseph packages; every package may import it.

Holds instruments (Instrument / Future / Option / Exchange / AssetType), contract specs, the
bar / tick / settlement / margin / fee DTOs, and the revision-record DTOs
(capability, version, source, revision id, digest, receipt plus immutable relative-path file list).

Does not hold: the DAL interface or preflight (joseph-dal), canonical JO order commands
(joseph-mini), factor definitions (joseph-alpha), vendor field mappings (provider plugins).

QuantLib: `Option` carries `exercise_style` (CFFEX index options are European) so it maps onto
QuantLib instruments; conversion helpers, if wanted, live in an optional `joseph-api[quantlib]`
extra and never in the core package.

Public contracts: https://github.com/hanzhichao2000/joseph-docs-public
