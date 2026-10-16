# Ratings and counters

The table describes ordinary live requests. “Review author” and “comment author” mean the same person for a top-level review. Unless stated otherwise, that person is not the item author, and the voter is neither author. A dash means no change.

| Action | Item rating | Comment rating | Item author's rating | Comment author's rating | Upvote counters | User history |
| --- | --- | --- | --- | --- | --- | --- |
| Upvote an item | `+1` | — | `+1` | — | Item `+1`, item author `+1` | Item author `+1` |
| Retract that vote | `-1` | — | `-1` | — | Item `-1`, item author `-1` | Item author `-1` |
| Write a positive review | `+5` | — | `+5` | — | — | Item author `+5` |
| Write a negative review | `-5` | — | `-5` | — | — | Item author `-5` |
| Write a neutral comment or reply | — | — | — | — | — | — |
| Upvote a positive review | `+1` | `+1` | — | `+1` | Comment `+1`, comment author `+1` | Comment author `+1` |
| Upvote a negative review | `-1` | `+1` | — | `+1` | Comment `+1`, comment author `+1` | Comment author `+1` |
| Upvote a neutral comment or reply | — | `+1` | — | `+1` | Comment `+1`, comment author `+1` | Comment author `+1` |
| Retract an eligible comment vote | Reverse its item delta | `-1` | — | `-1` | Comment `-1`, comment author `-1` | Comment author `-1` |
| Item author writes any comment on their own item | — | — | — | — | — | — |
| Another user upvotes the item author's comment | — | — | — | — | Comment `+1` only | — |
| Item author upvotes someone else's comment on their item | — | — | — | — | Comment `+1` only | — |

For example, a negative review with three eligible upvotes contributes `-8` to the item, `-5` to the item author, `+3` to the review author (from votes only), and `+3` to the comment's rating.

## Eligibility and special cases

- Users cannot upvote their own items or comments. Retraction supports existing self-votes by decrementing only the raw object upvote count.
- Item voting requires a non-deleted item with `visible` or `link_only` visibility. The API does not check expiration.
- Comment voting requires a non-deleted comment; its API does not check the parent item's deletion, visibility or expiration.
- A comment on its author's own item never contributes rating, even when someone else votes for it. An item author's vote on another person's comment also contributes no rating.
- Replies normally have `vibe=None`; they earn comment/user vote points but do not inherit the parent review's sign or affect item rating.
- Ordinary comment editing removes the vibe field from the form, so it cannot change the review's sign.
- Repeated vote requests normally do nothing after the first: hooks run only when a vote row was created or deleted. The counter functions themselves do not enforce eligibility or deduplication.

## Deletion and other counters

| Event or counter | Live behavior |
| --- | --- |
| Delete a comment | Reverse its initial review points on the item and item author, and eligible vote points on the item/comment/comment author; decrement its author's `comments_count`. Vote rows and the deleted comment's raw `upvotes` remain stored. |
| Delete a top-level comment | Also soft-delete its live direct replies, reverse their rating contributions, and decrement their authors' comment counts. The hook identifies replies by the deletion timestamp shared with the parent. |
| Delete a negative review with `n` eligible votes | Item gains `5 + n`; item author gains `5`; review author loses `n`; comment rating loses `n`; review author's upvotes lose `n`. See the null-voter discrepancy below. |
| Hide an item | Remove listing counts if previously listed; keep its rating and all user rating contributions. |
| Delete an item through the ordinary view | Soft-delete it and remove listing counts if previously listed. There is no rating rollback for its votes, reviews or comment votes. |
| `Item.comment_count` | Counts non-deleted top-level comments only, excluding replies. |
| `User.comments_count` | Counts all of the user's non-deleted comments, including replies and comments on their own items. |
| `Item.bookmark_count` | Increment on bookmark creation; decrement on removal only if the stored count is positive. No rating effect. |
| `User.items_count` | Listing count maintained by item creation/update/hide hooks. Recalculation uses non-deleted, visible, unexpired items. |
| Country/city `items_count` | Listing hooks increment/decrement the item's country and city. Items without a country are ignored by these hooks. |
| Category counts | Calculated from `Item.visible_objects()` and cached for 24 hours. Item lifecycle hooks bump a global cache version. |

In category counts, `everywhere` means **items with no country**, not all countries combined. A country selection includes its items; a city selection filters by city. Each root-category total includes its subcategories.

## Recalculation

The management command is:

```sh
uv run python manage.py recalculate_counters
```

This writes database totals, replaces rating history for every non-deleted user (including users whose new rating is zero), and invalidates the category cache. All database changes run in one transaction. It is not a dry run and was not executed for this change. Run it while writes are paused: a transaction prevents partial rebuilds but does not serialize concurrent vote/comment requests.

History is reconstructed with one entry per contributing item vote, review, or comment vote, using the source event timestamp and current item title. Review entries belong to the item author. Retracted votes, deleted reviews and their old reversal entries disappear. Users with no contributing events get an empty history; zero-total users with offsetting events retain those reconstructed events. Soft-deleted users are not recalculated and their history is preserved. The full rebuilt history sums to each recalculated user's rating; the UI still displays only the latest 100 entries.

| Rebuilt value | Source and filtering |
| --- | --- |
| Item/user points from item votes | Votes on non-deleted items, excluding identifiable self-votes. Null-user votes still count. |
| Item/item-author points from reviews | Non-deleted positive/negative comments on non-deleted items, excluding comments by the item author. |
| Comment/user points from comment votes | Votes on non-deleted comments and items, excluding comments by the item author and identifiable votes by either author. Null-user votes still count. Positive/negative review votes also adjust item rating with the review's sign. |
| Item/comment raw upvotes | All vote rows on non-deleted items/comments respectively, including votes excluded from ratings. Comment raw counts do not require a non-deleted parent item. |
| User upvotes | Votes eligible for rating under the rules above. |
| Item comment/bookmark counts | Non-deleted top-level comments; all bookmark rows. |
| User comment counts | Non-deleted authored comments, even if the parent item is deleted. |
| User item and geography counts | Non-deleted, visible, unexpired items. |
| Category cache | Increment global version and calculate worldwide root totals. Other buckets refill on demand. |

Rating and raw-upvote resets use the default managers, so soft-deleted objects' stored values are not generally reset. Drafts, link-only items and expired items are excluded from listing counts, but their rating contributions still count while the item is not deleted.

## Applying the review-recipient correction

Existing totals computed under the old rule still include review points assigned to reviewers. Run the recalculation command after deploying the corrected code to rebuild current totals with review points assigned to item authors. Until that rebuild, deleting an old review reverses points from its item author even though the old creation path credited or penalized its reviewer. The rebuild also has the broader effects described above. Existing `Rating` rows for recalculated users are deleted and replaced from the current contributing events under the corrected rule.

## Debugging leads

These are observations from the code; they do not establish which one caused a particular production symptom.

| Finding | Why it matters | Relevant code |
| --- | --- | --- |
| Item deletion and rebuild disagree | Live deletion leaves user rating/upvotes earned through the item intact. Recalculation excludes all rating contributions from deleted items, so user totals and reconstructed history can change afterward. | `delete_item()` in [items/views.py](../items/views.py); rebuild rating queries |
| Null voters are treated differently on comment deletion | Recalculation counts `CommentVote.user_id=None`, but `decline_comment_rating()` explicitly excludes them. A review that was rebuilt with such votes can leave residual user/item points when deleted. Null vote users are possible through `SET_NULL` on hard user deletion or imported data; soft deletion alone does not null the FK. | [comments/models.py](../comments/models.py), `decline_comment_rating()`, rebuild comment-vote query |
| Source changes and counter updates are separate transactions | Vote rows are created/deleted before the atomic counter helper runs. Comment saves/deletes also happen before their hooks; comment creation's helper is not atomic. A failure between steps can leave source rows, totals and history inconsistent. | [items/api.py](../items/api.py), [comments/api.py](../comments/api.py), [comments/views.py](../comments/views.py) |
| Comments on deleted items can still receive live vote updates | Comment APIs filter only comment deletion. Their hooks can update the comment author's rating even though rebuilding excludes the deleted parent item. | [comments/api.py](../comments/api.py), rebuild comment-vote query |
| Time-based expiry does not invoke listing hooks | Stored geography/user listing counts can remain stale after expiry until rebuilt. Category caches can also retain expired items until invalidation or timeout. | `Item.visible_objects()` / `is_listed`, [categories.py](categories.py) |
| Godmode item deletion skips listing counters | Generic admin deletion updates search for items but does not call `item_hidden()`, unlike the ordinary item deletion view. | `godmode_delete_model()` in [godmode/views/main.py](../godmode/views/main.py) |
| History display is limited | The full reconstructed history matches the rebuilt user rating, but the UI shows only 100 events. The displayed subset need not sum to `User.rating`. | [models.py](models.py), [views.py](views.py), rebuild command |

When investigating a mismatch, compare the source vote/comment rows, the stored counters, and the eligibility rules above. Recalculation can repair some drift, but it can also expose these differences; it does not prove that the live path and rebuild implement the same policy.
