# Cached media opportunities: real SigLIP

No cloud inference or external research results.

```json
{
  "model": "google/siglip-base-patch16-224",
  "revision": "7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed",
  "device": "cpu",
  "model_load_seconds": 6.659346000000369,
  "total_seconds": 212.48586209997302,
  "inference_seconds": 166.7379363994114,
  "seconds_per_candidate": 0.6750523740866858,
  "counts": {
    "ranking_opportunities": 247,
    "processed_locally": 247,
    "failures": 0,
    "deterministic_entity_resolved": 3,
    "high_confidence_ranking": 9,
    "high_confidence_with_strong_source": 0,
    "low_relevance": 91,
    "ambiguous": 147,
    "groq_candidate_checks_needed": 244,
    "research_handoff_zero_cached_candidate_groups": 85
  },
  "ranker_stats": {
    "ranked": 239,
    "batches": 150,
    "cache_hits": 8
  },
  "cloud_calls": {
    "groq": 0,
    "gemini": 0,
    "paid": 0
  },
  "gemini_needed": "Unknown until Groq returns unavailable/ambiguous; no live cloud calls made",
  "incremental_cloud_savings_from_siglip": 0,
  "limitations": [
    "SigLIP similarity is not calibrated identity probability.",
    "Entity-linked checks already avoided cloud before this phase.",
    "All-candidate counts are candidate checks, not measured provider requests.",
    "Top-3 in three-candidate smoke groups is a weak metric; Top-1 and margins matter.",
    "Cached candidate absence is not proof that no photograph exists on the web."
  ],
  "peak_working_set_mb": 1287.84765625
}
```

## Moti Dungri Mandir (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jaipur - Sri Moti Dungri Ganesh Ji Mandir (2022) - img 01.jpg | None | 0.3016904294490814 | AMBIGUOUS |

## Jantar Mantar (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.2794416695833206

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | A tree at Jantar Mantar (Jaipur, Rajasthan) 2012 (01).jpg | None | 0.4147266149520874 | AMBIGUOUS |
| 2 | A section of Jantar Mantar.jpg | None | 0.13528494536876678 | AMBIGUOUS |
| 3 | Jaipur, India, Jantar Mantar, Shadow.jpg | None | 0.003722546622157097 | LOW |

## Anokhi Museum of Hand Printing (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.5805741883814335

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Anokhi Museum of Hand Printing.jpg | None | 0.5829529762268066 | AMBIGUOUS |
| 2 | Anokhi Museum.jpg | None | 0.0023787878453731537 | LOW |

## Albert Hall Museum (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.8771261274814606

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Albert Hall museum, Jaipur.jpg | None | 0.9642207622528076 | HIGH |
| 2 | Albert Hall Museum, Jaipur 1.jpg | None | 0.08709463477134705 | AMBIGUOUS |
| 3 | Albert Hall (inside).JPG | None | 8.048569725360721e-06 | LOW |

## Sisodia Rani Palace and Garden (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.27504396438598633

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Rani Sisodia Garden.jpg | None | 0.9462777972221375 | AMBIGUOUS |
| 2 | Sisodia Rani Bagh, Jaipur, Rajasthan (DSCN4756).jpg | None | 0.6712338328361511 | AMBIGUOUS |
| 3 | Jeu De Lumières 2 (102580575).jpeg | None | 0.12713506817817688 | AMBIGUOUS |

## City Palace (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.032846271991729736

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | A gate in Jaipur city palace looking out to the Mubaraq Mahal.jpg | None | 0.4298247694969177 | AMBIGUOUS |
| 2 | A facade in City Palace complex, Jaipur.jpg | None | 0.396978497505188 | AMBIGUOUS |
| 3 | A light structure in the City Palace complex, Jaipur.jpg | None | 0.31820598244667053 | AMBIGUOUS |

## Birla Mandir (aka The Marble Temple) (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.5842486023902893

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jaipur - Birla Temple (7122464805).jpg | None | 0.9281485080718994 | HIGH |
| 2 | Balcony birla mandir.JPG | None | 0.3438999056816101 | AMBIGUOUS |
| 3 | Astik at Birla Mandir Jaipur.jpg | None | 0.09591155499219894 | AMBIGUOUS |

## Galtaji (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.6065944721922278

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | GaltaTempleOverview.jpg | None | 0.6180882453918457 | AMBIGUOUS |
| 2 | Monkey at Galtaji in Jaipur.jpg | None | 0.011493773199617863 | LOW |
| 3 | Rhesus macaques at Galtaji, Jaipur, Rajasthan, India | None | 0.0023960776161402464 | LOW |

## Govind Devji Temple (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.8877993486821651

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Govind Dev Ji Temple, Jaipur, 20191218 1059 9092.jpg | None | 0.9230601191520691 | HIGH |
| 2 | Echoes of ancient architecture.jpg | None | 0.035260770469903946 | LOW |
| 3 | Govind Dev Ji Temple (17059).jpg | None | 0.00721234455704689 | LOW |
| 4 | Barbajit Pur.jpg | None | 0.0003825186868198216 | LOW |

## Amrapali Museum (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.7421923130750656

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | AMRAPALI ASHOK MARG.png | None | 0.807531476020813 | HIGH |
| 2 | AMRAPALI MUSEUM, JAIPUR.jpg | None | 0.06533916294574738 | LOW |
| 3 | Bracelets from Assam.jpg | None | 0.0012242385419085622 | LOW |

## Shri Digamber Jain Atishya Kshetra Mandir, Sanghiji (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.26363372802734375

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Sangheji jain temple,sanganer,jaipur.JPG | None | 0.8418035507202148 | AMBIGUOUS |
| 2 | Ancient idol of Lord Parshvanath with other Tirthankaras at Sanghiji, Sanganer, Jaipur.jpg | None | 0.5781698226928711 | AMBIGUOUS |
| 3 | Digambar Jain temple in Noida Sector 50, Uttar Pradesh.jpg | None | 0.4600737690925598 | AMBIGUOUS |

## Jawahar Circle (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.10808300971984863

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jawahar Circle Garden, Jaipur, Rajasthan.jpg | None | 0.9604288339614868 | AMBIGUOUS |
| 2 | Patrika Gate Jawahar Circle Jaipur 2022-07.jpg | None | 0.8523458242416382 | AMBIGUOUS |
| 3 | ASHOK KUMAR 2026.jpg | None | 1.5417980421261746e-06 | LOW |

## Lake Palace (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.15516793727874756

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Umaid Lake Palace-Jaipur Agra National Highway-Rajasthan-IMG-1698.jpg | None | 0.43299898505210876 | AMBIGUOUS |
| 2 | 20191218 Jal Mahal Palace in Jaipur 1429 9234.jpg | None | 0.2778310477733612 | AMBIGUOUS |
| 3 | "Optical illusion", Water Palace, Jaipur, Rajasthan, India.jpg | None | 0.17756228148937225 | AMBIGUOUS |

## Dalaram Bagh (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.5834392756223679

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Amber Fort Garden View | None | 0.7939054369926453 | HIGH |
| 2 | Dilaram Bagh, Amber 2016.jpg | None | 0.2104661613702774 | AMBIGUOUS |

## Ram Niwas Garden (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.05690523982048035

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Albert Hall Museum (exterior), Ram Niwas Garden, Jaipur, Rajasthan, India (2016) 2 | None | 0.10719436407089233 | AMBIGUOUS |
| 2 | Albert Hall Museum, Ram Niwas Garden, Jaipur, Rajasthan, India (2009) 1.jpg | None | 0.05028912425041199 | LOW |
| 3 | Albert Hall Museum (exterior), Ram Niwas Garden, Jaipur, Rajasthan, India (2016) 6 | None | 0.03547743707895279 | LOW |

## Akabar Ke Kos Chinha (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.3387577682733536

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Kos minar 16 September 2024.jpg | None | 0.3499443829059601 | AMBIGUOUS |
| 2 | Kos minar IMG 20240916 121015 876.jpg | None | 0.011186614632606506 | LOW |

## Kesar Kyari (Jaipur, park)

Expected: None; correct reference rank: None; top margin: 0.16790078580379486

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | A garden on lake.jpg | None | 0.3535986542701721 | AMBIGUOUS |
| 2 | 500px photo (102577897).jpeg | None | 0.18569786846637726 | AMBIGUOUS |
| 3 | Amber Palace-Kesar Kyari Garden VJC-20131017.jpg | None | 0.14075809717178345 | AMBIGUOUS |

## Vidyadhar Garden (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.1276450753211975

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Vidyadhar Bagh | None | 0.7861520051956177 | AMBIGUOUS |
| 2 | Vidyadhar Bagh | None | 0.6585069298744202 | AMBIGUOUS |
| 3 | Jaipur, the Pink City | None | 6.292825128184631e-05 | LOW |

## Royal Gaitor (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.32632865011692047

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | 20111024 - 051 - Royal Gaitor.jpg | None | 0.3999977111816406 | AMBIGUOUS |
| 2 | 56807717 | None | 0.07366906106472015 | AMBIGUOUS |

## Stepwell Panna Meena (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Monsoon has came but old water reserves are dray because it not a good monsoon and these water reserves filled with rain water flowing down the surrounding hills and brought to these reserves by channels c - panoramio.jpg | None | 0.9897420406341553 | AMBIGUOUS |

## Jaipur Wax Museum (Jaipur, museum)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Kathputli at the Jaipur Wax Museum 04.jpg | None | 0.011507052928209305 | LOW |

## Diwan-i-Am (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jaipur, Fuerte Amber (2002) 16 | None | 0.4809897840023041 | AMBIGUOUS |

## Galwar Bagh (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 2.0736113924613164e-05

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | India at a Glance | None | 2.260859400848858e-05 | LOW |
| 2 | A shot of a bright tower in the monkey temple of jaipur.jpg | None | 1.8724800838754163e-06 | LOW |
| 3 | A shot of a bright tower in the monkey temple of jaipur.jpg | None | 1.3748472156294156e-06 | LOW |

## Jain Mandir (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | India - Jaipur - 023 - The peculiar Birla Mandir temple (1037308254) | None | 0.009645724669098854 | LOW |

## Gaitore (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.44525960087776184

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Gaitore Ki Chhatriya.jpg | None | 0.8517874479293823 | HIGH |
| 2 | Gatore chhatri in jaipur in landscape view.jpg | None | 0.4065278470516205 | AMBIGUOUS |
| 3 | 56807717 | None | 0.09433754533529282 | AMBIGUOUS |

## Statue Circle (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Statue Circle, Jaipur Rajasthan.jpg | None | 0.6011651754379272 | AMBIGUOUS |

## Patrika Gate (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Patrika gate Jaipur.jpg | None | 0.8579326272010803 | AMBIGUOUS |

## India gate (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jaipur, India, Gate.jpg | None | 0.0012932009994983673 | LOW |

## Maharaniyon (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Maharaniyon Ki Chhatriyan.jpg | None | 0.003758108476176858 | LOW |

## Sun Gate (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Amber Fort Jaipur- Suraj and Sun Gate Entrance.jpg | None | 0.01242160890251398 | LOW |

## Moon Gate (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | The Moon Gate (102577377).jpeg | None | 0.002053162083029747 | LOW |

## Ganesh Pol (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.14427244663238525

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ganesh Gate - Amber Fort - Jaipur | None | 0.9373914003372192 | AMBIGUOUS |
| 2 | Ganesh Pol | None | 0.793118953704834 | AMBIGUOUS |
| 3 | Ganesh Pol | None | 0.037950463593006134 | LOW |

## Sattais Kacheri (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Sattais Kacheri, Amber Fort, Jaipur, 20191219 1017 9532.jpg | None | 0.4881215989589691 | AMBIGUOUS |

## Elephant Riding (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.9689997402019799

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Elephant ride, Amber Fort | None | 0.9708794355392456 | HIGH |
| 2 | Amber Fort (Amber, 11Km from Jaipur) | None | 0.00187969533726573 | LOW |
| 3 | Amber Fort (Amber, 11Km from Jaipur) | None | 0.0018528292421251535 | LOW |

## Paanch Batti (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Panch Batti Circle Jaipur पांच बत्ती सर्किल (2022-07) 02.jpg | None | 0.37144985795021057 | AMBIGUOUS |

## Jawahar Kala Kendra (Jaipur, museum)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | 2022 July - JawaharKalaKendra Jaipur 13.jpg | None | 0.7985260486602783 | AMBIGUOUS |

## Sanganeri Gate (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Sanganeri Gate Jaipur.jpg | None | 0.8903689980506897 | AMBIGUOUS |

## Moti Doongri Fort (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Moti Doongri Fort, Jaipur; January 2024.jpg | None | 0.16902418434619904 | AMBIGUOUS |

## Haveli (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jaipur-Samode Haveli-20131017.jpg | None | 0.4152315855026245 | AMBIGUOUS |

## Man Gate (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jaipur city gates (4188500779).jpg | None | 0.9840936064720154 | AMBIGUOUS |

## Suraj Pol Gate (Jaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.3011907134205103

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Suraj-Pol, Amber Fort | None | 0.313732385635376 | AMBIGUOUS |
| 2 | Amer (25182306644) | None | 0.012541672214865685 | LOW |

## Udaipur (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Udaipur-Stadtpalast-42-vom Picholasee-2018-gje.jpg | None | 0.5715242028236389 | AMBIGUOUS |

## Bharatiya Lok Kala Mandal (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.025797421112656593

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Bearded knight with lance, folk art, Bharatiya Lok Kala Museum, Udaipur, India.jpg | None | 0.038230206817388535 | LOW |
| 2 | Bearded knight with scepter, folk art, Bharatiya Lok Kala Museum, Udaipur, India.jpg | None | 0.012432785704731941 | LOW |
| 3 | Ganesh, folk art, Bharatiya Lok Kala Museum, Udaipur, India.jpg | None | 0.00031315095839090645 | LOW |

## City Palace, Udaipur (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.49927201867103577

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Udaipur-Stadtpalast-04-2018-gje.jpg | None | 0.8698392510414124 | HIGH |
| 2 | 20191208 Pałac Miejski w Udajpurze 1541 7619 DxO.jpg | None | 0.3705672323703766 | AMBIGUOUS |
| 3 | 20191207 Lake Pichola, City Palace, Udaipur, 1516 7254.jpg | None | 0.34739288687705994 | AMBIGUOUS |

## Jag Mandir (Udaipur, religious)

Expected: None; correct reference rank: None; top margin: 0.9510511970388507

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jagmandir.jpg | None | 0.9510578513145447 | HIGH |
| 2 | Hotel jagmandir udaipur.jpg | None | 6.654275694017997e-06 | LOW |
| 3 | Hotel jagmandir udaipur bath.jpg | None | 5.445975226336941e-09 | LOW |

## Bagore-ki-Haveli (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.005562715232372284

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Udaipur, Dharohar, ghoomar dancers | None | 0.12970083951950073 | AMBIGUOUS |
| 2 | 20191207 Gangaur Ghat and Bagore Ki Haveli, Udaipur 1524 7266.jpg | None | 0.12413812428712845 | AMBIGUOUS |
| 3 | Udaipur, Dharohar, ghoomar dance | None | 0.09947379678487778 | AMBIGUOUS |

## Jagdish Temple, Udaipur (Udaipur, religious)

Expected: None; correct reference rank: None; top margin: 0.08520486950874329

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jagdish Temple | None | 0.5456278324127197 | AMBIGUOUS |
| 2 | JagdishTemple-Udaipur-Rajasthan JM34.jpg | None | 0.46042296290397644 | AMBIGUOUS |
| 3 | Détail des frises et des sculptures ornant le temple hindouïste Jagdish Mandir - A58851S.jpg | None | 0.16341231763362885 | AMBIGUOUS |

## Shiv Niwas Palace (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.2218974232673645

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Shiv niwas avanindra.jpg | None | 0.798485517501831 | AMBIGUOUS |
| 2 | City Palace Udaipuraryagraphy.jpg | None | 0.5765880942344666 | AMBIGUOUS |
| 3 | India-7041 - Flickr - archer10 (Dennis).jpg | None | 0.5369375348091125 | AMBIGUOUS |

## Chandpole (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.07331589609384537

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Udaïpur-VPL 07-Chand Pol footbridge-20131013.jpg | None | 0.18160951137542725 | AMBIGUOUS |
| 2 | Chandpole.jpg | None | 0.10829361528158188 | AMBIGUOUS |

## Monsoon Palace (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.008129656314849854

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Monsoon Palace (cropped).jpg | None | 0.991919755935669 | AMBIGUOUS |
| 2 | A front view of cloud palace.JPG | None | 0.9837900996208191 | AMBIGUOUS |
| 3 | 20191208 Pałac Monsunowy w Udajpurze 1215 7551.jpg | None | 0.9018515944480896 | AMBIGUOUS |

## Ahar Cenotaphs (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.1779676079750061

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | 1919 Cenatoph of Pannalal at Mahasatiya in Udaipur.jpg | None | 0.9709893465042114 | AMBIGUOUS |
| 2 | Ahar cenotaph.jpg | None | 0.7930217385292053 | AMBIGUOUS |
| 3 | Ahar Cenotaphs 7 | None | 0.03762776032090187 | LOW |

## Gulab Bagh and Zoo (Udaipur, park)

Expected: None; correct reference rank: None; top margin: 0.021532198414206505

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | GulabBagh Entrancec.jpg | None | 0.04595401510596275 | LOW |
| 2 | GulabBagh.jpg | None | 0.02442181669175625 | LOW |
| 3 | Fb nks.jpg | None | 0.009259418584406376 | LOW |

## Saheliyon-ki-Bari (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.0581093430519104

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | A fountain inside the garder of Sahelion Ki Bari, Udaipur.jpg | None | 0.9931496977806091 | AMBIGUOUS |
| 2 | Magical aura created by nature and architecture @ Garden of Maidens.jpg | None | 0.9350403547286987 | AMBIGUOUS |
| 3 | Architecture Saheliyon-ki-Bari (Courtyard of the Maidens).jpg | None | 0.13051272928714752 | AMBIGUOUS |

## Karni Mata, Udaipur (Udaipur, religious)

Expected: None; correct reference rank: None; top margin: 0.039670154452323914

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | KarniMata SideRoof.jpg | None | 0.13692139089107513 | AMBIGUOUS |
| 2 | Desi bharatiya udaipuri ooooncha! mandir.JPG | None | 0.09725123643875122 | AMBIGUOUS |
| 3 | KarniMata.jpg | None | 0.017246948555111885 | LOW |

## Pala Ganesh Temple (Udaipur, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | PalaGaneshUdaipur.jpg | None | 0.8664939999580383 | AMBIGUOUS |

## Pratap Park (Udaipur, park)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | I Love Udaipur.jpg | None | 0.8444068431854248 | AMBIGUOUS |

## Udaipur Solar Observatory (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.3443332016468048

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | USO Observatory | None | 0.6308754682540894 | AMBIGUOUS |
| 2 | Udaipur Solar Observatory 01.jpg | None | 0.28654226660728455 | AMBIGUOUS |

## Sajjangarh Biological Park (Udaipur, park)

Expected: None; correct reference rank: None; top margin: 0.03873204754199833

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Black Panda.jpg | None | 0.039851218461990356 | LOW |
| 2 | Badis Beauty.jpg | None | 0.0011191709199920297 | LOW |
| 3 | Bear standing on foot.jpg | None | 7.476711289200466e-06 | LOW |

## Agasthyavanam Biological Park (Udaipur, park)

Expected: None; correct reference rank: None; top margin: 2.3826832773465867e-07

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Agasthyakoodam Biosphere Reserve.jpg | None | 3.3032100077434734e-07 | LOW |
| 2 | Agasthyakoodam Biosphere Reserve 2.jpg | None | 9.205267303968867e-08 | LOW |
| 3 | Plant from Agasthyavanam.jpg | None | 7.127077594759612e-08 | LOW |

## Kingdom of Mewar (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: 0.2331500258296728

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Udaipur, Lal ghat | None | 0.24161483347415924 | AMBIGUOUS |
| 2 | Udaipur, Dharohar, chari dance | None | 0.008464807644486427 | LOW |
| 3 | Udaipur, Dharohar, ghoomar dance | None | 0.005036964081227779 | LOW |

## Ambrai Ghat (Udaipur, nature)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ambrai ghat.jpg | None | 0.23119120299816132 | AMBIGUOUS |

## Rajiv Gandhi Garden (Udaipur, park)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | RajivGandhiGarden-Statue.jpg | None | 0.046413354575634 | LOW |

## Vintage and Classic Car Museum (Udaipur, museum)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | 1934 Rolls-Royce in Vintage & Classic Car Collection Museum, Udaipur.jpg | None | 0.6483191251754761 | AMBIGUOUS |

## Sajjangarh (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Sajjangarh.jpg | None | 0.25607311725616455 | AMBIGUOUS |

## Moti Magari ke Prasad (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Moti Mahal, Maharana Pratap smarak-Moti Magri.jpg | None | 0.0018326707649976015 | LOW |

## Gangodbhav Kund (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Gangodbhav Kund.jpg | None | 0.9923306703567505 | AMBIGUOUS |

## Cenotaph of Raja Rama Shah's Sons, Ahar (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | அகர் நினைவுச் சின்னங்கள் Ahar Cenotaphs udaipur rajasthan2.jpg | None | 0.9433550238609314 | AMBIGUOUS |

## Meera Temple, Ahar (Udaipur, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Meera Temple Ahar Udaipur.jpg | None | 0.9734224081039429 | AMBIGUOUS |

## Sukhadia Circle (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Sukhadia circle, Udaipur, Rajasthan.jpg | None | 0.6221903562545776 | AMBIGUOUS |

## Taj Fateh Prakash Palace (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Udaipur, City Palace and Fateh Prakash Palace Hotel.jpg | None | 0.8890341520309448 | AMBIGUOUS |

## Chunda Palace (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | CHUNDA PALACE.jpg | None | 0.028969334438443184 | LOW |

## Shilpgram (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Shilpgram Udaipur 1.jpg | None | 0.10405709594488144 | AMBIGUOUS |

## Pratap Gaurav Kendra Rashtriya Tirth (Udaipur, museum)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Pratap Gaurav Kendra, Inauguration .jpg | None | 0.0052417670376598835 | LOW |

## Jagmandir Palace (Udaipur, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jagmandir Palace Udaipur.jpg | None | 0.00045416352804750204 | LOW |

## Ahar Museum (Udaipur, museum)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Grinding Stone, Ahar Museum.jpg | None | 3.80004621547414e-06 | LOW |

## Sankat Mochan Hanuman Temple (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: 0.009132985025644302

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | TULSI MANDIR BANARAS, UTTAR PRADESH | None | 0.03382137417793274 | LOW |
| 2 | Sankat Mochan temple entrance, Varanasi - IRCTC 2017 (1).jpg | None | 0.024688389152288437 | LOW |
| 3 | MINIATURE ART, TULSI MANDIR BANARAS, UTTAR PRADESH | None | 0.00011879874364240095 | LOW |

## Varanasi (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: 0.019696414470672607

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Varanasi, India, Varanasi skyline in the evening.jpg | None | 0.915497362613678 | AMBIGUOUS |
| 2 | Varanasi, India, Varanasi skyline in the evening.jpg | None | 0.8958009481430054 | AMBIGUOUS |

## Roman Catholic Diocese of Varanasi (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: 0.0016316608471242944

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | BHU (42504).jpg | None | 0.001651994651183486 | LOW |
| 2 | Kedharnath.jpg | None | 2.0333804059191607e-05 | LOW |

## Sarnath Museum (Varanasi, museum)

Expected: None; correct reference rank: None; top margin: 0.6751803806982934

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Art and Archeological Museum at Sarnath.JPG | None | 0.6829792261123657 | AMBIGUOUS |
| 2 | 003 Ramgram Stupa, 1st BCE.jpg | None | 0.007798845414072275 | LOW |
| 3 | 002 Railing, 2nd BCE.jpg | None | 0.00027505375328473747 | LOW |

## Scindia Ghat (Varanasi, nature)

Expected: None; correct reference rank: None; top margin: 0.040804505348205566

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Scindia Ghat (3620381973).jpg | None | 0.7575461268424988 | AMBIGUOUS |
| 2 | Scindia Ghat (3620381973).jpg | None | 0.7167416214942932 | AMBIGUOUS |

## Vishalakshi Temple (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | காசி விசாலாட்சி கோயில்.jpg | None | 0.009850251488387585 | LOW |

## Munshi Ghat (Varanasi, nature)

Expected: None; correct reference rank: None; top margin: 0.1844211220741272

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ahilyabai, Munshi, Darbhanga and Rana-Mahal Ghat, Varanasi.jpg | None | 0.9836695194244385 | AMBIGUOUS |
| 2 | Munshi Ghat 2.jpg | None | 0.7992483973503113 | AMBIGUOUS |
| 3 | Boats on the Ganges river at Munshi Ghat, Varanasi, India - October 2014.jpg | None | 0.541520357131958 | AMBIGUOUS |

## Bharat Mata Mandir (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: 0.14163564258706174

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Bharat Mata (6333841995).jpg | None | 0.14168430864810944 | AMBIGUOUS |
| 2 | Bharat Mata Mandir Varanasi India - panoramio (3).jpg | None | 4.866606104769744e-05 | LOW |
| 3 | Bharat Mata Mandir Varanasi India - panoramio.jpg | None | 3.360427669463206e-08 | LOW |

## Shri Tilbhandeshwar Mahadev Mandir (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Shri Tilbhandeshwar Mahadev Mandir0.jpg | None | 0.023943250998854637 | LOW |

## Man Singh Observatory (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: 0.013968020677566528

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Courtyard at Observatory of Man Singh.jpg | None | 0.3437942564487457 | AMBIGUOUS |
| 2 | View of Varanasi city from the roof top of Observatory of Man Singh.jpg | None | 0.3298262357711792 | AMBIGUOUS |
| 3 | Calculation figureat of Samrat Yantram 2 at Observatory of Man Singh.jpg | None | 0.0008269957033917308 | LOW |

## Nepali Mandir (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Nepali Temple exterior, Varanasi.jpg | None | 0.368802547454834 | AMBIGUOUS |

## Lalita Ghat (Varanasi, nature)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Lalita ghat Varanasi.JPG | None | 0.928987443447113 | AMBIGUOUS |

## Dalmia Bhawan (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: 0.2825581803917885

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Dalmia House 1.jpg | None | 0.3281809389591217 | AMBIGUOUS |
| 2 | Dalmia House 3.jpg | None | 0.04562275856733322 | LOW |
| 3 | Dalmia House 2.jpg | None | 1.1787932407969492e-06 | LOW |

## Assi River (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: 0.12037742137908936

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Assi River.jpg | None | 0.8578143119812012 | AMBIGUOUS |
| 2 | Assi Ghat (46848).jpg | None | 0.7374368906021118 | AMBIGUOUS |

## Chaukhandi Stupa (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: 0.021040499210357666

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Chaukhandi Stupa on a hill, Sarnath.jpg | None | 0.9486705660820007 | AMBIGUOUS |
| 2 | Chaukhandi Stupa 1.JPG | None | 0.9276300668716431 | AMBIGUOUS |
| 3 | Chaukhandi Stupa on a hill, Sarnath.jpg | None | 0.9155970811843872 | AMBIGUOUS |
| 4 | Chaukhandi Stupa 2.JPG | None | 0.8084768652915955 | AMBIGUOUS |

## Varuna River (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: 0.009775365644600242

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Varanasi.Cantonment.JPG | None | 0.010370809584856033 | LOW |
| 2 | Front View of Buddhist temple at Sarnath, Varanasi, India | None | 0.000595443940255791 | LOW |
| 3 | A distant view of Buddhist temple at Sarnath, Varanasi, India | None | 1.0508626473892946e-05 | LOW |

## Dhamek Stupa (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: 0.009720325469970703

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | 14. Dhamek Stupa, Sarnath.jpg | None | 0.9752030372619629 | AMBIGUOUS |
| 2 | 026 Dhamekh Stupa, Sarnath (9237176593).jpg | None | 0.9654827117919922 | AMBIGUOUS |
| 3 | 027 Dhamekh Stupa, Sarnath (9239946602).jpg | None | 0.9470062851905823 | AMBIGUOUS |

## Lion Capital of Asoka (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Sarnath capital.jpg | None | 0.9891513586044312 | AMBIGUOUS |

## Manikarnika Ghat (Varanasi, nature)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Manikarnika Cremation Ghat, Varanasi.jpg | None | 0.7731618285179138 | AMBIGUOUS |

## Baba Keenaram Sthal (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Baba Keenaram Sthal.jpg | None | 0.0015610208502039313 | LOW |

## Tulsi Ghat (Varanasi, nature)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Tulsi Ghat.jpg | None | 0.626437783241272 | AMBIGUOUS |

## Durga Mandir, Varanasi (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Durga Temple gate.JPG | None | 0.745141863822937 | AMBIGUOUS |

## New Vishwanath Temple (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | New Vishwanath Temple at BHU.jpg | None | 0.8701168894767761 | AMBIGUOUS |

## Tulsi Manas Mandir (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Manas Mandir.jpg | None | 0.02923770062625408 | LOW |

## Sankata Devi Mandir (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Varanasi 110m - tree shrines (34892136202).jpg | None | 0.06326419860124588 | LOW |

## Kaal Bhairav Mandir, Varanasi (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Kaal Bhairab, Kathmandu, Nepal.jpg | None | 0.3186012804508209 | AMBIGUOUS |

## Parshvanath Jain temples, Varanasi (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jain Mandir.JPG | None | 0.038653187453746796 | LOW |

## Alamgir Mosque (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ganga bird 07.jpg | None | 0.6832913756370544 | AMBIGUOUS |

## Ganga Mahal Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ganga Mahal Ghat next to Assi Ghat on the Ganges, Varanasi.jpg | None | 0.3593551218509674 | AMBIGUOUS |

## Jagadamba Nepali Dharmashala (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Jagadumba Nepali Dharamshala Varanasi.jpg | None | 0.3609757125377655 | AMBIGUOUS |

## Ratneshwar Mahadev temple (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Matri-rin Temple in Varanasi.jpg | None | 0.0313541479408741 | LOW |

## Sarnath Deer Park (Varanasi, park)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Sarnath Deer Park.jpg | None | 0.0004992984468117356 | LOW |

## Indian Institute of Technology (BHU) Varanasi (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Dept of Electrical Engineering IIT-BHU.jpg | None | 0.6590930223464966 | AMBIGUOUS |

## Lal Khan Tomb (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Tomb of Lal Khan.jpg | None | 0.8564019799232483 | AMBIGUOUS |

## Stay Banaras (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Anura (51693).jpg | None | 1.866475329848072e-08 | LOW |

## Dalmandi (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Dalmandi.png | None | 0.00037057537701912224 | LOW |

## Mrityunjay Mahadev Mandir (Varanasi, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Mrityunjay Mahadev Mandir (73147).jpg | None | 0.02775212936103344 | LOW |

## Moti Jhīl (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Moti Jhīl.jpg | None | 0.03374715521931648 | LOW |

## Shivala Ghat (Varanasi, nature)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Shivala Ghat Varanasi, 2011-08-22.jpg | None | 0.8696302175521851 | AMBIGUOUS |

## Narad Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Narad Ghat, Varanasi, 6 April 2019.jpg | None | 0.9933686852455139 | AMBIGUOUS |

## Harishchandra Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | India-varanasi-Cremation-Harishchandra-Ghat-Flickr-Dennis.jpg | None | 0.31629809737205505 | AMBIGUOUS |

## Ranamahal Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ranamahal Ghat, Varanasi.JPG | None | 0.9113616943359375 | AMBIGUOUS |

## Manmandir Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | A laid back evening at the Manmandir ghat, Varanasi, Uttar Pradesh.jpg | None | 0.7956984639167786 | AMBIGUOUS |

## Lali Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Devdepawali at Lali Ghat Varanasi 20.jpg | None | 0.0001314700930379331 | LOW |

## Chousatti Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Varanasi 2010 Chousatti Ghat.JPG | None | 0.9419949054718018 | AMBIGUOUS |

## Dr. Rajendra Prasad Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Dr Rajendra Prasad Ghat Sewage Pumping Station.jpg | None | 0.710555911064148 | AMBIGUOUS |

## Chauki Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Varanasi, Chauki Ghat (8748088196).jpg | None | 0.7250244617462158 | AMBIGUOUS |

## Raj Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Varanasi, Gopal Govardhan Puja Sansthan, Raj Ghat (2013).jpg | None | 0.0874466523528099 | AMBIGUOUS |

## Ram Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ram Ghat, Varanasi.JPG | None | 0.9781543612480164 | AMBIGUOUS |

## Prahlad Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Prahlad Ghat, Varanasi.JPG | None | 0.7992600202560425 | AMBIGUOUS |

## Sakka Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Varanasi India, Sakka Ghat (6884799148).jpg | None | 0.853952944278717 | AMBIGUOUS |

## Trilochan Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Trilochan Ghat, Varanasi.JPG | None | 0.6239798665046692 | AMBIGUOUS |

## Shitala Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Shitala Ghat, Varanasi.JPG | None | 0.5573345422744751 | AMBIGUOUS |

## Badrinarayan Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Badrinarayan Ghat, Varanasi.JPG | None | 0.920052707195282 | AMBIGUOUS |

## Telianala Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Telianala Ghat, Varanasi.JPG | None | 0.9753830432891846 | AMBIGUOUS |

## Ashokan Pillar (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ashokan Pillar, Sarnath, Varanasi, Uttar Pradesh.jpg | None | 0.6522015929222107 | AMBIGUOUS |

## Ashram (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Prepartion sequence of Bhandara at Lalibaba Ashram at Lalighat Varanasi led by Lalibaba for Dev Deepabali night 29.jpg | None | 8.045560662139906e-09 | LOW |

## Lolark Kund (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Lolark Kund, Varanasi, Uttar Pradesh.jpg | None | 0.00010562962415860966 | LOW |

## Swastika (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | India - Varanasi Swastika - 0425.jpg | None | 0.06558864563703537 | LOW |

## Namo Ghat, var (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Namaste sculpture at Namo Ghat Varanasi.jpg | None | 0.016177784651517868 | LOW |

## Gularia Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Gularia Ghat.jpg | None | 0.2758667767047882 | AMBIGUOUS |

## Vaccharaja Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Vaccharaja Ghat, Varanasi.JPG | None | 0.16179576516151428 | AMBIGUOUS |

## Brahma Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Brahma Ghat, Varanasi.JPG | None | 0.9969680905342102 | AMBIGUOUS |

## Meer Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Mir Ghat (291262278).jpg | None | 0.3789399564266205 | AMBIGUOUS |

## Nishadraj Ghat (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Nishadraj Ghat, Varanasi.JPG | None | 0.9505123496055603 | AMBIGUOUS |

## Aircraft (Varanasi, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | SpiceJet aircraft at Varanasi Airport.jpg | None | 0.21483857929706573 | AMBIGUOUS |

## Manali (Manali, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Hadimba Devi Mandir.jpg | None | 0.3342031240463257 | AMBIGUOUS |

## Leh–Manali Highway (Manali, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Highway To Thrill (233024297).jpeg | None | 0.09157612919807434 | AMBIGUOUS |

## Bhrigu Lake (Manali, nature)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Bhrigu Lake by Ahmad Faiz Mustafa (4).jpg | None | 9.68329914030619e-05 | LOW |

## Hidimba Devi Temple, Dhungri Manali (Manali, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Hidimba Temple Manali.jpg | None | 0.9926614761352539 | AMBIGUOUS |

## National Highway 3 (Manali, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Best place to drive,Rohtang pass.jpg | None | 0.00511030713096261 | LOW |

## Miniature Siva Temple, Jagatsukh (Manali, religious)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Miniature Shiv Temple.jpg | None | 0.8002310991287231 | AMBIGUOUS |

## Tourist locations in Manali (Manali, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Grass Deodar Monsoon Mist Manali Sep20 R16 04026.jpg | None | 1.6903449306937546e-08 | LOW |

## Old Manali (Manali, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Old Manali 2.jpg | None | 3.0800849344814196e-05 | LOW |

## Vashist Hot Water Springs and Temple (Manali, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ghotkach Temple Manali.jpg | None | 8.686557703185827e-05 | LOW |

## Kartik Temple (Manali, heritage)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Ghotkach Temple Manali.jpg | None | 2.6603074729791842e-05 | LOW |

## Museum of Himachal Culture & Folk Arts (Manali, museum)

Expected: None; correct reference rank: None; top margin: None

| Rank | Candidate | Reference | Similarity | Confidence |
|---|---|---|---|---|
| 1 | Chhattahar , a traditional Kullu necklace Museum of Himachal Culture and Folk Arts, Manali, Himachal Pradesh.jpg | None | 0.0017970760818570852 | LOW |
