import Link from "next/link";
import type { GuideMeta } from "@/lib/guides";

/**
 * Star Wars Unlimited beginner guide, built around the Intro
 * Battle: Hoth product. Second post on the ``/guides/`` surface.
 *
 * Tentpole: May The Fourth 2026. Evergreen after that --
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
  updatedAt: "2026-05-02",
  disclosure: "amazon-creator-connections-swu",
  draft: false,
  tags: ["star-wars-unlimited", "beginners", "trading-card-games"],
};

const ASMODEE_HOTH_HREF =
  "https://store.asmodee.com/products/star-wars-unlimited-intro-battle-hoth";
const HOTH_HREF =
  "https://www.amazon.com/dp/B0FLQ68H1G?ref=t_ac_view_request_product_image&campaignId=amzn1.campaign.1L1498A4C8CX0&linkCode=tr1&tag=orangediscoun-20&linkId=amzn1.campaign.1L1498A4C8CX0_1776824144789";
const TWO_PLAYER_STARTER_HREF =
  "https://www.amazon.com/s?k=Star+Wars+Unlimited+Two-Player+Starter+Set&tag=orangediscoun-20";
const A_LAWLESS_TIME_BOOSTER_HREF =
  "https://www.amazon.com/s?k=Star+Wars+Unlimited+A+Lawless+Time+Booster+Box&tag=orangediscoun-20";
const A_LAWLESS_TIME_SPOTLIGHT_HREF =
  "https://www.amazon.com/s?k=Star+Wars+Unlimited+A+Lawless+Time+Spotlight+Deck&tag=orangediscoun-20";

// eslint-disable-next-line jarvis/function-length -- Long-form guide body is editorial content, not control flow.
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
        this.&quot; By 2026 the launch rush is over. The format
        has settled into recognizable archetypes, the first
        rotation arrived with A Lawless Time in March, and the
        Intro Battle line is the cleanest on-ramp Fantasy Flight
        has shipped for this TCG.
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
          <strong>Any card can become a resource.</strong> During
          regroup, you may put one card from hand face-down as a
          resource. That means fewer MTG-style non-games where
          you miss land drops, and less Pokemon-style deck math
          around separate energy counts.
        </li>
        <li>
          <strong>Alternating actions.</strong> SWU does not make
          one player take a full turn while the other waits. In
          the action phase, players go back and forth taking one
          action at a time: play a card, attack, use an action
          ability, take initiative, or pass.
        </li>
        <li>
          <strong>Space and ground arenas.</strong> The zones are
          spatially separated &mdash; TIE fighters don&apos;t
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
          rel="noopener noreferrer"
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
          <strong>Two-Player Starter Set.</strong> Two 50-card
          decks in one box, plays out of the box, teaches both
          sides of the table. Older starters still move around
          Amazon and LGS shelves in the $25&ndash;40 range,
          depending on set and inventory. If you have a friend
          who also wants to try SWU, this is the clear best buy.
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
          factions, tutorial-style booklet, labeled game board,
          reference cards, and counters. Publisher price is
          $19.99, with Amazon pricing changing day to day. This
          is the path if you want to learn at your own pace
          before pulling anyone else in.
        </li>
      </ul>
      <p>
        The Intro Battle: Hoth is one of three valid picks. It&apos;s
        the right pick if you learn better solo; the Two-Player
        Starter is the right pick if you already have someone to
        play with.
      </p>

      <h2>What the Intro Battle: Hoth starter gets you</h2>
      <p>
        The publisher&apos;s{" "}
        <a
          href={ASMODEE_HOTH_HREF}
          rel="noopener noreferrer"
          target="_blank"
        >
          Asmodee product page
        </a>{" "}
        positions Intro Battle: Hoth as a self-contained first
        game, with Vader&apos;s Imperial army against Leia
        Organa&apos;s Rebel defense of Echo Base.
      </p>
      <ul>
        <li>
          Two pre-built Hoth-themed decks for both sides of the
          engagement: Darth Vader&apos;s Imperial army and Leia
          Organa&apos;s Rebel defense of Echo Base.
        </li>
        <li>
          A tutorial-style rulebook that walks a new player
          through the first few turns at real pace, not a dense
          reference manual.
        </li>
        <li>
          The boxed components Asmodee lists for the set: 104
          cards, six reference cards, a game board, an info sheet,
          a rulebook, 57 damage counters, two epic action
          counters, and one initiative counter.
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
          <strong>Your next purchase.</strong>{" "}
          <a
            href={TWO_PLAYER_STARTER_HREF}
            data-affiliate-network="amazon"
            data-affiliate-placement="guide-swu-intro-hoth-compare-twoplayer"
            rel="sponsored noopener"
            target="_blank"
          >
            Two-Player Starter
          </a>{" "}
          if you want two decks to keep playing with a friend; an{" "}
          <a
            href={A_LAWLESS_TIME_SPOTLIGHT_HREF}
            data-affiliate-network="amazon"
            data-affiliate-placement="guide-swu-intro-hoth-compare-spotlight"
            rel="sponsored noopener"
            target="_blank"
          >
            A Lawless Time Spotlight Deck
          </a>{" "}
          if you want the current preconstructed single-deck
          path; or an{" "}
          <a
            href={A_LAWLESS_TIME_BOOSTER_HREF}
            data-affiliate-network="amazon"
            data-affiliate-placement="guide-swu-intro-hoth-compare-booster"
            rel="sponsored noopener"
            target="_blank"
          >
            A Lawless Time booster box
          </a>{" "}
          if you want sealed or limited packs for store events.
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
      <p>
        <em>
          As an Amazon Associate rollforstore.com earns from
          qualifying purchases. This post contains affiliate links.
        </em>
      </p>
    </>
  );
}
