# spokenform 0.2.3 downstream handoff

After the first fixed `spokenform` patch is published, the kokorog2p adapter
should require:

```text
spokenform>=0.2.3,<0.3.0
abbr2words>=0.2.4,<0.3.0
```

The downstream implementation should then:

1. remove the local `eins Kubikmeter` compatibility regex;
2. add direct-vs-public German extended-quantity parity coverage;
3. run the complete seven-language migration suite; and
4. release only after those checks pass against the released package.

The spokenform-side real run-level German gate is in
`tests/test_real_kokorog2p_integration.py` and covers area, volume, speed,
aliases, and protected spans. Publication remains a manual operator action for
this task.
