import Link from "next/link";
import type { GuideMeta } from "@/lib/guides";

/**
 * Star Wars Unlimited beginner guide, built around the Intro
 * Battle: Hoth product. Second post on the ``/guides/`` surface.
 *
 * Tentpole: May The Fourth 2026. Evergreen after that &mdash;
 * the slug and body intentionally avoid date-stamping so the
 * post keeps ranking after the tentpole passes.
 *
 * Copy follows the editorial brief at
 * ``Team/data/marketing/briefs/rfs-guide-swu-intro.md``.
 */
export const meta: GuideMeta = {
  slug: "star-wars-unlimited-beginner",
  title:
    "Star Wars Unlimited for MTG/Pokemon players: a May The Fourth intro",
  description:
    "A beginner's guide to Star Wars Unlimited for MTG and Pokemon players: how SWU plays differently, three ways to start, and what the Intro Battle: Hoth gets you.",
  author: { name: "Roll For Store Editorial" },
  publishedAt: "2026-04-21",
  disclosure: "amazon-creator-connections",
  draft: false,
  tags: ["star-wars-unlimited", "beginners", "trading-card-games"],
};

const HOTH_HREF =
  "https://www.amazon.com/dp/B0FLQ68H1G?ref=t_ac_view_request_product_image&campaignId=amzn1.campaign.1L1498A4C8CX0&linkCode=tr1&tag=orangediscoun-20&linkId=amzn1.campaign.1L1498A4C8CX0_1776824144789";

export default function StarWarsUnlimitedBeginner() {
  console.assert(
    meta.slug === "star-wars-unlimited-beginner",
    "StarWarsUnlimitedBeginner: meta.slug must match registry key",
  );
  console.assert(
    meta.draft === false,
    "StarWarsUnlimitedBeginner: post must be published",
  );

  return (
    <>
      <p>
        May the Fourth is a manufactured holiday, but it&apos;s
        also the one day each year when every TCG-adjacent
        retailer points at Star Wars Unlimited and says &quot;try
        this.&quot; By 2026 the launch rush is over. The first
        big rotation hasn&apos;t hit. The format has settled into
        recognizable archetypes, booster boxes are priced
        reasonably for a still-growing game, and the Intro Battle
        line is the cleanest on-ramp Fantasy Flight (now under
        Asmodee) has ever shipped for a TCG.
      </p>
      <p>
        This guide is aimed at MTG and Pokemon players who are
        curious about a swap, or just want a second TCG in the
        rotation. SWU isn&apos;t going to replace your main game
        &mdash; but it&apos;s the most forgiving &quot;different
        game, same muscle memory&quot; landing pad out there.
      </p>

      <h2>What makes SWU feel different from MTG / Pokemon</h2>
      <p>
        A few specifics the official rules page won&apos;t put in
        a bullet list:
      </p>
      <ul>
        <li>
          <strong>Dual-sided cards.</strong> Every card in your
          deck can be played as a unit or flipped face-down to
          become a resource. That means fewer dead draws than MTG
          (no stuck-on-two-lands opening) and tighter deck math
          than Pokemon (no trainer-vs.-energy ratio to agonize
          over).
        </li>
        <li>
          <strong>Simultaneous combat phases.</strong> Both
          players engage during the combat step rather than
          waiting on a strict priority stack. Turns run shorter
          than MTG&apos;s, which is the biggest ergonomic
          improvement for players burning out on 45-minute casual
          games.
        </li>
        <li>
          <strong>Space and ground arenas.</strong> The zones are
          spatially separated &mdash; tie fighters don&apos;t
          fight stormtroopers at the same time. It feels closer
          to Hearthstone&apos;s board than to MTG&apos;s creature
          stack, and MTG converts adjust faster than they expect.
        </li>
      </ul>
      <p>
        If you&apos;re coming from another TCG, the quickest way
        to feel the difference is to play a full game. Rules
        reference lives at{" "}
        <a
          href="https://starwarsunlimited.com"
          rel="noopener"
          target="_blank"
        >
          starwarsunlimited.com
        </a>
        .
      </p>

      <h2>Three ways to start</h2>
      <p>
        Not a ranked list &mdash; three honest paths depending on
        your situation.
      </p>
      <ul>
        <li>
          <strong>Starter Deck alone.</strong> Cheapest option.
          Requires a friend who already plays and has their own
          deck. Works well if your LGS crowd has already picked up
          the game.
        </li>
        <li>
          <strong>Two-Player Starter Set.</strong> Two decks in
          one box, plays out of the box, teaches both sides of
          the table. Current sets run $25&ndash;40 depending on
          which you pick up. If you have a friend who also wants
          to try SWU, this is the clear best buy.
        </li>
        <li>
          <strong>
            Intro Battle sets (e.g.,{" "}
            <a
              href={HOTH_HREF}
              data-affiliate-network="amazon"
              data-affiliate-placement="guide-swu-intro-hoth"
              rel="sponsored noopener"
              target="_blank"
            >
              Intro Battle: Hoth
            </a>
            ).
          </strong>{" "}
          Structured learning path, themed around iconic
          factions, tutorial-style booklet walking you through
          the first few turns. Street price around $20. The path
          if you want to learn alone at your own pace before
          pulling anyone else in.
        </li>
      </ul>
      <p>
        The Intro Battle: Hoth is one of three valid picks. It&apos;s
        the right pick if you learn better solo; the Two-Player
        Starter is the right pick if you already have someone to
        play with.
      </p>

      <h2>What the Intro Battle: Hoth starter gets you</h2>
      <ul>
        <li>
          Pre-constructed Hoth-themed decks for both sides of the
          engagement &mdash; Rebel and Imperial.
        </li>
        <li>
          A tutorial-style rulebook that walks a new player
          through the first few turns at real pace, not a dense
          reference manual.
        </li>
        <li>
          Enough components (cards, tokens, base markers) to
          teach one player the core loop in a single afternoon.
        </li>
        <li>
          <strong>Not a competitive kit.</strong> Cards are
          fixed-rarity, chosen for clarity and teaching value
          rather than power level. If you love SWU after playing
          through the Intro Battle, your next purchase should be
          a Two-Player Starter or a booster box &mdash; not more
          Intro Battles.
        </li>
      </ul>
      <p>
        Think of this as the same role Pokemon&apos;s Battle
        Academy plays: a learn-the-game product, not a
        competitive entry.
      </p>

      <h2>After your first game &mdash; next steps</h2>
      <ul>
        <li>
          <strong>Find an LGS running SWU events.</strong> Most
          stores that run MTG Friday Night or Pokemon league
          nights have added SWU casual or sealed evenings in the
          last year.{" "}
          <Link href="/near-me">
            Find a local game store running Star Wars Unlimited
          </Link>{" "}
          &mdash; calling ahead is still the most reliable way to
          confirm a store runs SWU specifically.
        </li>
        <li>
          <strong>Join a playgroup.</strong> SWU&apos;s official
          Discord and subreddit are both active, but in-person
          learning wins. The{" "}
          <Link href="/stores/california">
            local game stores by state
          </Link>{" "}
          directory is the fastest way to find a host within
          driving distance.
        </li>
        <li>
          <strong>Your next purchase.</strong> Two-Player Starter
          if you want two decks to keep playing with a friend; a
          set booster box if you want sealed/limited in your
          pocket for store events.
        </li>
      </ul>

      <h2>SWU vs. MTG vs. Pokemon: a one-table gut check</h2>
      <table>
        <thead>
          <tr>
            <th scope="col"></th>
            <th scope="col">MTG</th>
            <th scope="col">Pokemon</th>
            <th scope="col">SWU</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Learning curve</th>
            <td>Steep</td>
            <td>Gentle</td>
            <td>Moderate</td>
          </tr>
          <tr>
            <th scope="row">Game length (casual 1v1)</th>
            <td>20&ndash;40 min</td>
            <td>15&ndash;25 min</td>
            <td>15&ndash;25 min</td>
          </tr>
          <tr>
            <th scope="row">Secondary market stability</th>
            <td>High</td>
            <td>High</td>
            <td>Building</td>
          </tr>
          <tr>
            <th scope="row">Competitive scene (2026)</th>
            <td>Mature</td>
            <td>Mature</td>
            <td>Growing</td>
          </tr>
          <tr>
            <th scope="row">Best on-ramp product</th>
            <td>Jumpstart / Starter Kit</td>
            <td>ETB / Battle Academy</td>
            <td>Two-Player Starter or Intro Battle</td>
          </tr>
        </tbody>
      </table>
      <p>
        SWU&apos;s secondary market is genuinely still building
        &mdash; don&apos;t oversell it to yourself. That&apos;s
        not a reason to skip the game; it&apos;s a reason to buy
        boxes you want to play with rather than speculate on.
      </p>

      <h2>Common first-game mistakes</h2>
      <ul>
        <li>
          Forgetting you can flip cards to the resource row on
          your own turn. New players end up resource-starved in a
          system specifically built to prevent that.
        </li>
        <li>
          Ignoring the space arena because it &quot;feels&quot;
          like a side zone. It isn&apos;t &mdash; space wins
          matter as much as ground wins.
        </li>
        <li>
          Building around one faction leader too early. The Intro
          Battle deck is balanced. Trust it for the first few
          games before swapping in your favorite card.
        </li>
        <li>
          Buying booster boxes before finishing a full game. Play
          first, buy second. The Intro Battle is built to teach
          that exact sequencing.
        </li>
      </ul>

      <h2>Quick FAQ</h2>
      <p>
        <strong>
          Is SWU worth learning if I already play MTG?
        </strong>{" "}
        Yes, if your MTG complaint is turn length or decision
        fatigue. Not if you&apos;re looking for MTG&apos;s
        card-interaction depth &mdash; SWU is deliberately simpler
        at the stack level.
      </p>
      <p>
        <strong>Will my MTG sleeves fit?</strong> Standard TCG
        card size (63&times;88 mm). Your existing MTG or Pokemon
        sleeves work fine.
      </p>
      <p>
        <strong>Can I play SWU at my local MTG store?</strong>{" "}
        Most LGS are adding SWU casual nights.{" "}
        <Link href="/near-me">
          Check /near-me to find one near you
        </Link>{" "}
        and call ahead to confirm the night runs regularly.
      </p>

      <p>
        May the Fourth is the excuse. If you&apos;ve been thinking
        about a TCG swap, the Intro Battle: Hoth is the cheapest
        way to find out whether SWU works for you without
        committing to booster-box money. It&apos;s a teaching
        product; treat it as one, not as your main deck. If the
        game sticks, level up to a Two-Player Starter or a booster
        box next. Either way &mdash;{" "}
        <Link href="/near-me">pick it up locally</Link> if you can,
        rather than waiting on shipping.
      </p>
    </>
  );
}
