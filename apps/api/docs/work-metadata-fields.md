# Work metadata field coverage

The consolidated work panel covers animation and visual novels. A display
revision records selected field labels and source references. Values are read
from the current evidence, including any staff role, episode range, or edition
qualifier. The synopsis can be rewritten in a separate revision per language.
The original title comes directly from a source name, with its language when
known. Unclear fields and empty placeholders are omitted.

## Verified source coverage

| Source | Sample and verified field groups |
| --- | --- |
| Bangumi | [Frieren season 2](https://bgm.tv/subject/515759) and [CLANNAD](https://bgm.tv/subject/13). The [subject API](https://bangumi.github.io/api/) returns the title, synopsis, media, and a flexible infobox. The infobox carries broadcast, official links, production roles and their episode scopes, and visual novel engine, platform, development, and publishing details. Page credit roles vary by record. |
| MyAnimeList | [The Apothecary Diaries Season 3](https://myanimelist.net/anime/61987/Kusuriya_no_Hitorigoto_3rd_Season) and [Frieren season 2](https://myanimelist.net/anime/59978/Sousou_no_Frieren_2nd_Season). The authenticated [v2 API](https://myanimelist.net/apiconfig/references/api/v2) returned titles, dates, broadcast, format, status, duration, source material, studios, content classification and favorites. The API combines Genres, Themes, and Demographics into one array. The [editorial directory](https://myanimelist.net/anime.php) supplies the category IDs used to separate them. The tested endpoint omitted the separately requested producers and licensors shown on the website. |
| AniList | [ONE PIECE](https://anilist.co/anime/21/ONE-PIECE) and [Frieren season 2](https://anilist.co/anime/182255). The [Media API](https://docs.anilist.co/reference/object/media) supplies native, romanized and English names, synonyms, origin, format, status, dates, season, duration, genres, source material, hashtag, studios, producers and next airing. The next airing timestamp expires in the read model. Weighted and mean scores and popularity signals stay in ranking. |
| VNDB | [CLANNAD](https://vndb.org/v4). The [Kana VN and release endpoints](https://api.vndb.org/kana) expose original-script titles, translations, dates, language and platform lists, development, original length category, edition-specific credits, and release details. Release language, media, voice coverage, resolution, age classification, and producers belong to the release. User-reported play times and voted tags stay outside the work display fields. |

Editorial Genres and MAL's editorial Themes and Demographics can appear in the
display. Provider user tags, votes, ratings, rankings, collection labels, and
favorites stay outside the display and model input. Content classification
such as PG-13 is a separate publication field. The canonical relationship
read models continue to select episode, credit and related-work data by
provider. The work panel may show a source credit line as text.

## Coverage in the deployed catalogue

The November 23, 2026 read-only audit found 30,813 MAL anime records with a
revision. All those revisions had alternative titles and a studio key. Only
7 had a genre key, 4,899 had broadcast, and 30,258 included a content rating.
MAL omits some inapplicable values, so the latter two counts are not target
totals. The live detail endpoint returned Genres and favorites for both
sample works. The saved revisions lacked those values.

AniList had 29,519 anime records, with 22,050 saved revisions. Of those,
21,532 included the fuller description, studios, genres and synonyms keys.
The saved ONE PIECE record held the lighter schedule-shaped payload. Its
live response and page provided the missing work metadata.

The saved Bangumi infoboxes for Frieren season 2 and CLANNAD contained 58 and
21 rows respectively, matching the live API samples. The saved VNDB CLANNAD
payload contained language, platform, and staff fields. Its live Kana response
also exposed the edition and original length fields that the saved payload lacked.

## Refreshing existing works

After deploying the new projection, preview a page of existing works missing
the current mapper. A seasonal snapshot is not marked as a full-detail
refresh. Existing full details take precedence over seasonal promotion.

```sh
uv run python -m scripts.refresh_work_metadata mal --limit 20
uv run python -m scripts.refresh_work_metadata anilist --after 21 --limit 20
```

Use `--apply` to fetch and reproject the selected page. Each work commits in
its own transaction. Use the reported cursor to continue, or restart from
the beginning to see records that still need the new mapping. This refresh
does not run the metadata model. Production model eligibility is controlled
by the configured source policy.
