# Provisional SigLIP calibration

Eight visually checked, source-linked real photographs, each paired with two explicit cross-place distractors. Scores are sigmoid similarity values, not verified identity probabilities. Reference contact sheet: `scratch/siglip_reference_contact.png`. Model code follows the [model card](https://huggingface.co/google/siglip-base-patch16-224).

| POI | Correct rank | Wrong ranks | Correct score | Largest wrong score | Top margin | Decision |
|---|---:|---|---:|---:|---:|---|
| Albert Hall Museum | 1 | 2,3 | 0.964221 | 0.000002 | 0.964219 | HIGH |
| Sisodia Rani Palace and Garden | 1 | 2,3 | 0.946278 | 0.000000 | 0.946278 | HIGH |
| Birla Mandir (aka The Marble Temple) | 1 | 2,3 | 0.928149 | 0.000314 | 0.927835 | HIGH |
| Galtaji | 1 | 2,3 | 0.618088 | 0.000223 | 0.617865 | AMBIGUOUS |
| Kesar Kyari | 1 | 2,3 | 0.140758 | 0.005826 | 0.134932 | AMBIGUOUS |
| City Palace, Udaipur | 1 | 2,3 | 0.869839 | 0.004694 | 0.865145 | HIGH |
| Bhrigu Lake | 1 | 2,3 | 0.000097 | 0.000000 | 0.000097 | LOW |
| Hidimba Devi Temple, Dhungri Manali | 1 | 2,3 | 0.992661 | 0.000000 | 0.992661 | HIGH |

Top-1: 8/8. Top-3: 8/8 (weak measure with only three candidates). Clear cases: 5; ambiguous: 2; low: 1; incorrect: 0.

Observed correct scores span 0.00009683–0.992661; largest distractor score 0.005826. The correct Bhrigu Lake image scores very low. LOW must not reject a photograph or invalidate strong source evidence.

The configurable high threshold is the midpoint between the moderate Galtaji reference (.618088) and the weakest high-score reference, City Palace (.869839). The minimum is the midpoint between the strongest distractor (.005826) and Kesar Kyari (.140758). The margin is the midpoint between Kesar Kyari (.134932) and Galtaji (.617865). This separates the observed clusters conservatively; it is not a universal validation threshold.

```json
{
  "high_relevance": 0.743963748216629,
  "min_relevance": 0.07329191989265382,
  "ambiguity_margin": 0.37639855653833365
}
```

HIGH requires a leading candidate, enough relevance and a margin over at least one competitor. Single-candidate groups remain ambiguous by score; deterministic P18 evidence can still resolve them. Model/revision changes disable this calibration. Same-place close candidates need source/identity assurance. The smoke is small and selected, not a held-out accuracy estimate. There are no qualifying cached cafe/food candidate groups, so that requested optional category was unavailable. No non-photo acceptance/rejection threshold was recalibrated without labelled non-photo data.

Fresh smoke: 6.69s load; 12.11s for 24 candidates in eight batches; 0.504s/candidate; 1211MB peak working set. Cached weights were reused under HF_HUB_OFFLINE=1.
