# Account and Runner are separate entities

The first version serves individual Runners only, where login identity and runner are the same person. We still model Account (who logs in) and Runner (who is analyzed) separately, with an Account owning one or more Runners, so that the later Operator version (coaches, physiotherapists, stores managing many Runners) needs no data migration. In the first version each Account gets exactly one Runner, created automatically, and the interface does not expose the distinction.
