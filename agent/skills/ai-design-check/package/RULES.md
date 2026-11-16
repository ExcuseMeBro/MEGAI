# Enmera design rules

[Türkçe](RULES.tr.md) · Generated from `rules.json`; edit that file, then run `npm run docs`. Rules marked **checked** are found by `npx @enmera/ai-design-check`; the others are reviewed by people and agents.

## Writing

### Sentence case for interface text

`sentence-case` · error · checked

**Rule:** Only the first word and proper names start with a capital letter: "Rank tracking", "Site health". No automatic title-casing helper; text shows as written.

**Why:** Title Case on every short label reads loud and is not Turkish (or modern English UI) style. Microsoft's Turkish style guide: only proper nouns and the first word.

**How to fix:** Keep proper names (Google Business Profile, Search Console), official category and document names, abbreviations (AI, SERP) and language-code badges as they are. After a path separator the first word stays capitalised: "Site health › Site audit".

### No tracked uppercase labels

`no-decorative-uppercase` · warning · checked

**Rule:** No small uppercase, letter-spaced labels (kickers, eyebrows, section captions such as "NAVIGATION").

**Why:** It is the most common generated-UI template and hurts reading: we recognise words by shape.

**How to fix:** Write the label in sentence case with normal tracking. Codes, language codes and initials avatars may stay uppercase.

### Labels fit their slot

`short-labels` · note · review

**Rule:** A menu item or tab label that gets truncated is shortened, using the same word for the same thing everywhere.

**Why:** A cut label hides the meaning and looks unfinished.

**How to fix:** Shorten the label; do not shrink the font.

### No full stop on buttons and labels

`no-trailing-period-labels` · note · checked

**Rule:** Buttons, tabs, menu items and short labels end without a full stop; sentences in help text keep theirs.

**Why:** A full stop turns a command into a sentence and makes a row of buttons uneven.

**How to fix:** Remove the final full stop.

### Short placeholders

`short-placeholders` · note · checked

**Rule:** No "Search anything...", "Type here..." or "Enter your email here"; a placeholder is one or two words or an example value.

**Why:** Wordy placeholders repeat the label, disappear when typing and read as filler.

**How to fix:** "Search", or an example such as "name@company.com".

### Text is not cut off

`text-not-clipped` · warning · checked

**Rule:** Labels, buttons and table cells show their whole text at 320 px. Truncation with an ellipsis is allowed only where the full text is one tap away (title, tooltip, detail view).

**Why:** A cut-off label can change meaning ("Delete all…" of what?), and translations are often 30–40 % longer than English.

**How to fix:** Let the text wrap; if it truly must be one line, keep the full text in a title and in the detail view.

## Type scale

### Font sizes from the scale only

`type-scale` · error · checked

**Rule:** Use the theme scale: text-2xs (11 px, the smallest), text-xs, text-sm, text-base and up. No arbitrary text-[10px] or text-[13px].

**Why:** One-off sizes pile up into screens that are almost, but not quite, the same. Text under 11 px is a legibility failure.

**How to fix:** Add --text-2xs: 0.6875rem (line height 1rem) to the theme and map 9–11 px to it, 12 px to text-xs, 13 px to text-sm. Display sizes on marketing pages go in the allow list.

### Text styles that follow Dynamic Type

`dynamic-type` · warning · checked

**Rule:** In SwiftUI, set text with text styles (.body, .headline, .caption) or a custom font with relativeTo, not a fixed .system(size:). Icons may use a fixed size.

**Why:** A fixed size ignores the reader's text size setting, so people who need larger text cannot read the screen, and every screen ends up with its own ad hoc sizes.

**How to fix:** Map each size to the nearest text style (11 caption2, 12 caption, 13 footnote, 15 subheadline, 17 body, 20 title3, 22 title2, 28 title, 34 largeTitle) and keep the weight with .fontWeight.

### Headings at regular to semibold weight

`no-heavy-headings` · warning · checked

**Rule:** No font-extrabold or font-black (weight 800–900) in interface headings and numbers; hierarchy comes from size and position.

**Why:** Generated screens make every heading as heavy as possible, so nothing reads as more important.

**How to fix:** Use 400–600 and a step up in size. A display face that is designed heavy can be allowed in config.

### Emphasis with weight or colour, not italic

`no-italic-emphasis` · note · checked

**Rule:** Interface text is not set in italic for emphasis; quotes and titles of works may be italic.

**Why:** Italic is harder to read at interface sizes and looks like a placeholder.

**How to fix:** Use font-medium or the secondary text colour.

### No negative tracking on small text

`no-tight-small-text` · warning · checked

**Rule:** tracking-tight and negative letter spacing belong to large display text (40 px and up), never to text-base and smaller.

**Why:** Small letters squeezed together lose their shapes and become hard to read.

**How to fix:** Leave tracking at 0 for small text; slightly positive is fine for muted captions.

### Text is not shrunk to fit

`no-shrunk-text` · warning · checked

**Rule:** Body text and labels keep their size on phones (never below 12 px, never smaller than on desktop); only large headlines may scale down.

**Why:** Phones are read at arm's length and in sunlight; shrinking text to make a layout fit moves the problem to the reader.

**How to fix:** Keep the size and let the layout give: wrap, stack, or move secondary content below.

## Corners and surfaces

### Corner radii from the scale only

`radius-scale` · error · checked

**Rule:** Use rounded-md … rounded-3xl and rounded-full; large marketing surfaces get one shared token (rounded-panel). Arbitrary radii only for micro elements up to 5 px and for drawn device or icon shapes.

**Why:** 28, 30 and 32 px side by side read as noise, not as a system.

**How to fix:** Pick the nearest scale step or add one named token.

### No cards inside cards

`no-nested-cards` · warning · review

**Rule:** Group inside a card with spacing, type and dividers, not another bordered card.

**Why:** Nested frames add depth without meaning.

**How to fix:** Flatten: a divider or a muted background block instead of a second border and shadow.

### Inner corners follow the outer ones

`nested-radius` · warning · review

**Rule:** An element inside a rounded container uses radius = outer radius − padding (never below 4 px); not every element is a full pill.

**Why:** Equal radii inside and out make the gap look uneven at the corners; pills everywhere erase the difference between controls and containers.

**How to fix:** A 16 px card with 8 px padding holds 8 px items; keep full pills for chips and avatars.

### Cards rest on surface steps, not heavy shadows

`no-heavy-card-shadow` · warning · checked

**Rule:** Cards and panels in the page flow use a hairline border or a surface one step lighter than the page; shadow-lg and larger are for things that float (menus, dialogs, popovers).

**Why:** Every high-rated dashboard we studied separated cards with a light page background and white or raised cards, with almost no shadow; heavy shadows make a grid of cards look like floating stickers.

**How to fix:** Drop the shadow to shadow-sm or none and step the surface (page gray-50, card white; dark: page #0b0d14, card #11141c).

## Components and reuse

### Interactive elements come from shared components

`use-shared-components` · warning · checked

**Rule:** Pages use the shared Button, Input, Select, Textarea and Checkbox components, not raw <button>, <input>, <select> or <textarea>. Raw elements live only inside the component folder.

**Why:** Every raw element is a new copy of the button: one place gets a different height, focus ring or radius, and the next fix misses it.

**How to fix:** Replace it with the component; if the component lacks a variant, add the variant to the component.

### Badges, boxes, headings and button links come from shared components

`use-shared-looks` · warning · checked

**Rule:** A span styled as a badge, a div styled as a card, a heading with its own size classes or a link styled as a button is a hand-made copy of a shared component. Use the badge, box, heading and link-button components; the project names them in config.looks.

**Why:** Badges and boxes drift fastest: the same 'new' label ends up in five paddings and four greens. A heading scale only holds when headings pick a size instead of writing one.

**How to fix:** Replace the element with the component and pick a tone and size; if none fits, add a tone or size to the component, not a class at the call site.

### No visual overrides on shared components

`no-style-overrides` · warning · checked

**Rule:** className on Button, Badge, Input, Card and other shared components only places them (width, margin, alignment, grid position). Colour, radius, padding, height, font and border come from the component's variant and size props.

**Why:** An override is a hidden fork of the component: the same button looks different on two screens, which is exactly what a design system exists to stop.

**How to fix:** Move the look into a named variant or size of the component and use that.

### Repeated markup becomes a component

`repeated-markup` · warning · checked

**Rule:** The same long class list repeated in several places (a card, a badge, a stat tile, a section heading) is extracted into one shared component.

**Why:** Copies drift: one gets a new padding, another keeps the old radius. One component means one fix and less code.

**How to fix:** Extract the element into a component (or a variant of an existing one) and replace the copies.

### Few, quiet badges

`no-badge-spam` · warning · review

**Rule:** PRO, New and Beta badges are rare, text-only and have a reason; counts and shortcuts are plain text or a keycap, not glowing pills.

**Why:** Badges on every row stop meaning anything and add noise to the menu.

**How to fix:** Keep one badge where it changes a decision; remove the rest.

### One status system

`status-system` · warning · review

**Rule:** Statuses are a small tinted pill with a dot and a word, from one shared map (success, pending, failed, draft); the same status has the same colour on every screen.

**Why:** Status colour is learned once; when "Pending" is amber in one table and blue in another, people stop trusting colour at all.

**How to fix:** Create one StatusBadge with a status → tone map and use it in every table and card.

## Selectors

### One selector language

`selector-language` · error · review

**Rule:** A primary choice that changes the content (page tabs, topic groups, separate lists) is a segmented control. Its sub-tabs sit on the same row to its right as plain text (selected one on a light fill). Filters that narrow the same list are pill chips inside the list.

**Why:** Two stacked selector rows of similar weight hide which one is the main choice. Underlined tabs were tried and rejected.

**How to fix:** Never two selector rows on top of each other and no underline tabs. A small variant switch inside a card is a small segmented control.

## Layout

### Wide tables span the page

`full-width-tables` · warning · review

**Rule:** A data table with several columns takes the full width; the last column absorbs the spare width (w-full, cells max-w-0 truncate) so date and value never drift apart.

**Why:** Squeezed into a side column it truncates names; with few rows it leaves an empty area below.

**How to fix:** Move the side cards below the table into a two-column masonry.

### Uneven cards in a grid masonry

`masonry` · warning · checked

**Rule:** Cards of different heights go into a grid-based masonry (two columns, left-to-right order). No CSS columns, and no narrow column with empty space under it.

**Why:** CSS columns split shadows at the column top in Chrome and order cards column by column.

**How to fix:** Use a grid masonry component that places each card into the shortest column.

### Readable line length and leading

`readable-measure` · warning · review

**Rule:** Running text stays under about 80 characters per line (max-w-prose / max-w-3xl) with line height of at least 1.3; headings have more space above than below.

**Why:** Long lines lose the reader on the way back.

**How to fix:** Cap the paragraph width, not the card.

### Spacing with rhythm

`spacing-rhythm` · note · review

**Rule:** Related items sit tight, sections breathe. The same gap everywhere has no rhythm.

**Why:** Grouping is read from spacing before anything else.

**How to fix:** Use two or three steps: inside a group, between groups, between sections.

### Spacing on the 4 px grid

`spacing-scale` · warning · checked

**Rule:** Arbitrary spacing and sizes in px (mt-[13px], h-[31px], gap-[7px]) sit on the 4 px grid; prefer the theme steps.

**Why:** Off-grid values are what a model types when it guesses; rows and gaps drift apart by a pixel or two and the screen looks uneven.

**How to fix:** Round to the nearest theme step (mt-3, h-8, gap-2).

### One primary action in a hero

`hero-one-action` · warning · review

**Rule:** A hero has one primary and at most one secondary action; no third button, no chips or avatar rows stacked under the buttons.

**Why:** Each extra action splits attention at the moment the visitor decides whether to stay.

**How to fix:** Keep the main action and one alternative; move the rest further down the page.

### One card header pattern

`card-header-pattern` · warning · review

**Rule:** Every card header is the same: title on the left, at most one control on the right (period selector, "See all" or a ⋯ menu), on one baseline.

**Why:** Repeating one header across cards is what makes a dense dashboard calm; mixed headers make every card a new reading task.

**How to fix:** Extract a CardHeader component with title and an optional action slot and use it everywhere.

### One primary action per page

`one-primary-action` · warning · review

**Rule:** A page header has one filled primary button (usually top right); other actions are secondary, ghost or in a menu.

**Why:** Two filled buttons side by side ask the user to choose before they know what the page is for.

**How to fix:** Keep the action that moves the page's job forward filled; demote the rest.

### No sideways scrolling on phones

`no-horizontal-overflow` · error · checked

**Rule:** At 320 px the page is no wider than the screen. Wide content (a table, a code block) scrolls inside its own box, never the page.

**Why:** A page that scrolls sideways hides its right edge and makes every vertical scroll wobble.

**How to fix:** Let rows wrap (flex-wrap), allow long words to break (hyphens: auto with the right lang, overflow-wrap), wrap wide tables in overflow-x-auto.

### Phones get the same content

`no-hidden-content-narrow` · note · checked

**Rule:** Text shown on desktop is not hidden on phones (hidden sm:block). A collapsed menu is fine when the items stay one tap away.

**Why:** Hiding content to make a small layout work removes information from the majority of visitors.

**How to fix:** Show it, shorten it for everyone, or move it lower on the page instead of hiding it.

## Navigation

### Menu grouped by job, place decided first

`menu-by-job` · warning · review

**Rule:** Before building a feature decide its place: which menu section, its own row or a tab of an existing page, which URL prefix. Pages of the same job are one menu row with tabs. Sections collapse; the current one stays open.

**Why:** Without it a menu grows into a flat list of fifty rows where related work sits in four places.

**How to fix:** A moved address answers with 301 (path and query kept); callback URLs registered with outside services never move. Help texts name the same path as the menu.

## Visual language

### Line icons, not emoji

`icons-not-emoji` · warning · checked

**Rule:** Interface marks are line icons from one set (lucide). Emoji and text glyphs such as ✓ ★ are not used as UI decoration; emoji that are content (an emoji picker) stay.

**Why:** Emoji render differently on every platform and read as generated.

**How to fix:** Replace with the matching icon at the text size.

### No gradient text or purple gradients

`no-ai-gradients` · error · checked

**Rule:** Text is solid colour. No purple, violet or indigo gradients and no decorative radial halos behind sections.

**Why:** They are the most recognisable tells of generated interfaces.

**How to fix:** Use the brand colour flat; colour carries meaning (state, series, selection).

### No coloured side stripe on cards

`no-side-stripe` · warning · checked

**Rule:** No thick coloured border on one side of a card or alert.

**Why:** It is the single most common generated-UI accent and fights the rounded corner.

**How to fix:** Use a status badge, an icon or a light tinted background.

### Glow only in charts

`glow-in-charts-only` · warning · checked

**Rule:** Coloured glow shadows belong to the chart language (score rings, chart lines) only; buttons, cards and text do not glow.

**Why:** Glow everywhere is noise; glow on data draws the eye to the number.

**How to fix:** Remove it, or list the chart component in the allow list.

### Legible contrast

`legible-contrast` · warning · review

**Rule:** Text meets WCAG AA (4.5:1, large text 3:1); no grey text on coloured backgrounds.

**Why:** Grey on colour looks washed out and fails readers in sunlight.

**How to fix:** Use a darker shade of the background colour or near-white.

### No icon tile above every heading

`no-icon-tile-stack` · warning · review

**Rule:** A grid of identical cards each with a rounded icon tile, a heading and two lines of text is a template, not a layout. Use the icon inline or not at all, and vary what leads.

**Why:** It is the default output of every generator and says nothing about the product.

**How to fix:** Lead with the real content (a number, a screenshot, an example) instead of an icon.

### No announcement pill above the headline

`no-announcement-pill` · warning · checked

**Rule:** No "✨ Introducing X 2.0" pill above a hero headline unless it links to real, recent news; then it is a quiet text link.

**Why:** It is the most copied hero template; the eye lands on it before the headline and finds nothing.

**How to fix:** Remove it, or turn it into a plain link with a date.

### No sparkle icon for anything AI

`no-sparkle-for-ai` · note · checked

**Rule:** A sparkle does not mark every AI feature; use an icon that says what the action does (write, summarise, translate), or none.

**Why:** Sparkles are on every AI product, so they tell the user nothing about the button.

**How to fix:** Replace with a verb icon (PenLine, ListChecks, Languages) or text only.

### No blurred colour blobs behind content

`no-blur-blobs` · warning · checked

**Rule:** No large blurred shapes (blur-2xl, blur-3xl) or radial colour washes as decoration behind text and cards.

**Why:** Blobs are the default backdrop of generated pages; they lower contrast and say nothing about the product.

**How to fix:** Use one plain surface, or a real product view as the visual.

### One accent, used where it means something

`one-accent` · warning · review

**Rule:** The accent colour covers a few percent of the screen: the primary action, the selection and one key figure. Surfaces, borders and labels stay neutral.

**Why:** When everything is highlighted nothing stands out, and the screen loses the one place the eye should land.

**How to fix:** Count the accent on a screenshot; move it off chrome and onto the one thing that matters.

### Show the product, not a generic visual

`show-the-product` · warning · review

**Rule:** The main visual is the product itself or one concrete object from its world; no glossy blobs, orbs, robots, glowing brains or stock circuits.

**Why:** A generic visual could sit on any product page, so it explains nothing and makes the page look like a template.

**How to fix:** Use a real screen with real data, or an object that says what the product does.

### Solid buttons, no gradient fills

`no-gradient-buttons` · warning · checked

**Rule:** Buttons and button links use one solid fill from the theme; no gradient backgrounds, including the "Ask AI" button.

**Why:** In the dashboards we studied the strongest work used flat primary buttons; gradient buttons appeared on the AI features of weaker shots and read as decoration, not as the main action.

**How to fix:** Use the primary colour as a flat fill; mark an AI action with a verb, not a gradient.

## Accessibility

### Never remove the focus ring without a replacement

`focus-ring-removed` · error · checked

**Rule:** outline-none / outline-hidden only together with a visible focus-visible style (ring, outline or border) on the same element.

**Why:** Keyboard users lose their place. WCAG 2.4.7 (focus visible), 2.4.11 (focus not obscured).

**How to fix:** Add focus-visible:ring-2 (or the component's focus style); prefer outline-hidden over outline-none in Tailwind 4 so forced-colours mode keeps an outline. Dialog and popover containers receive focus programmatically and are exempt.

### Icon-only buttons have a name

`icon-button-name` · error · checked

**Rule:** A button or link that shows only an icon carries aria-label (or title, or visually hidden text).

**Why:** Screen readers announce "button" with no purpose; WCAG 4.1.2 name, role, value.

**How to fix:** Add aria-label with the action in sentence case ("Delete keyword").

## Motion

### Pulse only for live data

`pulse-for-live-only` · note · checked

**Rule:** A pulsing dot means something is running right now; it never decorates.

**Why:** Fake liveness teaches people to ignore real alerts.

**How to fix:** Bind the animation to the running state; show a static dot otherwise.

### No auto-scrolling strips

`no-marquee` · warning · checked

**Rule:** Content does not scroll by itself.

**Why:** It demands attention and always hides half of its content.

**How to fix:** A static, swipeable row or a short list.

### Transition named properties, not all

`no-transition-all` · warning · checked

**Rule:** No transition-all / transition: all; animate transform and opacity, transition colours by name.

**Why:** transition: all animates layout and size changes nobody intended and costs frames.

**How to fix:** transition-colors, transition-opacity, transition-transform or transition-[width].

### No bounce or overshoot easing on interface

`no-bounce-easing` · warning · checked

**Rule:** No animate-bounce and no cubic-bezier that overshoots for controls, panels and lists.

**Why:** Bounce reads as toy-like and dated on working screens and slows repeated actions.

**How to fix:** ease-out for entering, ease-in for leaving, 150–300 ms.

### Respect reduced motion

`reduced-motion` · note · review

**Rule:** Decorative and large motion stops or shrinks under prefers-reduced-motion (motion-safe: / motion-reduce:).

**Why:** Motion triggers vestibular discomfort; WCAG 2.3.3.

**How to fix:** Prefix long or looping animations with motion-safe:.

### No growing on hover

`no-hover-scale` · warning · checked

**Rule:** Cards and buttons do not scale up on hover; hover changes colour or surface, press may scale down slightly (0.97–0.98).

**Why:** Growing elements push their neighbours visually, blur text and read as a template effect.

**How to fix:** Replace hover:scale-105 with a background or border step; use active:scale-[0.98] for press feedback.

### Animate transform and opacity, not position

`no-layout-animation` · warning · checked

**Rule:** Transitions do not animate top, left, right, bottom, margin or padding; movement uses transform. Width on a progress meter is fine.

**Why:** Position and spacing changes re-run layout every frame and stutter on slower devices.

**How to fix:** Use translate and opacity (transition-transform, transition-opacity).

## Data and numbers

### Numbers carry their comparison

`numbers-with-context` · warning · review

**Rule:** A headline number shows what it is compared with ("−1.2 vs last week") and, if it moves over time, its recent history.

**Why:** "Average rank 13.8" alone does not say whether that is good news.

**How to fix:** Add the delta and its period under the number.

### Empty data shows an empty state

`empty-states` · warning · review

**Rule:** No data means an empty state with the next step, never an empty chart or a table of dashes.

**Why:** An empty chart looks broken.

**How to fix:** Say why it is empty and what fills it (connect, run, wait for the first check).

### Tabular numerals in tables and KPIs

`tabular-numbers` · note · review

**Rule:** Numbers that are compared or update (table columns, KPIs, counters, timers) use tabular-nums and right alignment in tables.

**Why:** Proportional digits make columns jagged and values jump as they change.

**How to fix:** Add tabular-nums to the cell or the table; text-end for numeric columns.

### Plausible sample data

`no-placeholder-data` · warning · checked

**Rule:** No Lorem ipsum, John Doe, $123,456 or [X] in screens, demos and screenshots; sample data looks like real data from the product's world.

**Why:** Filler data makes a finished screen look like a mock-up and hides layout problems that real lengths would show.

**How to fix:** Use realistic names, amounts with uneven digits and real lengths.

### Stat cards read label, value, change

`stat-card-anatomy` · warning · review

**Rule:** A stat card has three lines in this order: a short muted label, the value large and tabular, then the change with its period ("+1.5% vs last month"). No icon tiles, sparklines or emoji competing with the number.

**Why:** This was the most consistent pattern across the professional dashboards we studied: the eye reads down one column, and the change is meaningless without its period.

**How to fix:** Reorder to label → value → change; put the period next to every change.

### Charts highlight one thing

`chart-highlight-one` · warning · review

**Rule:** Bars and series are neutral; the accent goes on the one that matters (the current period, the selected point), with its value labelled on the chart. Category charts use one hue in steps, not a rainbow.

**Why:** The professional work we studied kept inactive bars light grey and lit one; the weaker shots used five or six hues, which turns a chart into a legend lookup.

**How to fix:** Grey out every series but one; label it directly; collapse small categories into "Other".

### Label series on the chart

`direct-labels` · note · review

**Rule:** With three series or fewer, put the name or value at the end of the line or on the bar instead of a separate legend.

**Why:** A legend makes the reader match colours back and forth; a direct label is read once.

**How to fix:** Move the legend text next to its series; keep a legend only for many series.

### Dim the digits that matter less

`dim-secondary-digits` · note · review

**Rule:** In a headline figure the cents, decimals or unit are set in the secondary text colour ($422,525.82 with .82 muted), so the significant part reads first.

**Why:** The strongest hero numbers we studied used this one detail instead of any decoration.

**How to fix:** Wrap the fraction in a span with the secondary colour; keep the same size.

## Localisation

### Case changes name the locale

`locale-aware-case` · warning · checked

**Rule:** toUpperCase()/toLowerCase() on interface text use toLocaleUpperCase(locale)/toLocaleLowerCase(locale).

**Why:** Turkish i/İ and ı/I: "istanbul".toUpperCase() is "ISTANBUL", not "İSTANBUL".

**How to fix:** Pass the interface locale; for keys and ids the plain methods are fine (allow-list them).

### Numbers, dates and money through the locale formatter

`locale-number-format` · warning · checked

**Rule:** Interface numbers go through the project's formatter (Intl with an explicit locale). No toFixed(), no toLocaleString() without a locale, no "$" + value.

**Why:** 1,255.00 vs 1.255,00: the wrong separator misreads by a factor of a thousand; server and browser render different text.

**How to fix:** Use the shared format helper; keep raw toFixed() only for machine values.

### Plurals through the plural system

`no-naive-plural` · warning · checked

**Rule:** No count === 1 ? "item" : "items" and no + "s": plurals go through the i18n plural form (trans_choice, ICU, Intl.PluralRules).

**Why:** Languages have up to six plural categories; English-only logic breaks every translation.

**How to fix:** Use the plural helper of the i18n layer with the count.

### No sentences glued from pieces

`no-concatenated-translation` · warning · checked

**Rule:** A sentence is one translation key with placeholders, never t('a') + value + t('b').

**Why:** Word order differs by language: Turkish puts the verb last.

**How to fix:** One key: t(':count keywords on page one', { count }).

## Interaction

### Filters react instantly

`instant-filters` · note · review

**Rule:** A filter's value updates in local state at once; the list does not fade while reloading; tabs are prefetched.

**Why:** Waiting for the server before the control moves feels broken.

**How to fix:** Optimistic local value, background reload without a progress bar, prefetch on tabs.

## Copy

### No marketing buzzwords

`no-buzzwords` · warning · checked

**Rule:** No streamline, empower, supercharge, seamless, cutting-edge, next-generation, world-class, revolutionize. Say what it does, with a number if there is one.

**Why:** These words are instant tells of generated copy and promise nothing measurable.

**How to fix:** Replace the claim with the measured fact.

### Buttons say what they do

`specific-action-labels` · warning · checked

**Rule:** No Submit, OK, Click here, Yes/No: the label names the action and its object ("Save changes", "Delete keyword").

**Why:** Generic labels force people to read the whole dialog and make destructive buttons easy to hit by mistake.

**How to fix:** Verb + object, sentence case.

### Errors say what happened and what to do

`error-copy` · warning · checked

**Rule:** No "Oops", "Something went wrong", "An error occurred", "Invalid input": name the problem and the next step.

**Why:** A vague error leaves people stuck and creates support tickets (GOV.UK error message guidance).

**How to fix:** "Enter a date in the past", "The file is over 5 MB: choose a smaller one".

### Ellipsis character, not three dots

`ellipsis-character` · note · checked

**Rule:** "Loading…", "Search…" use the single … character.

**Why:** Three periods break differently and read as a typo next to real typography.

**How to fix:** Replace ... with … in interface strings.

### No exclamation marks in interface copy

`no-exclamation-copy` · warning · checked

**Rule:** Labels, numbers, toasts and headings state things plainly: no "!" or "!!", including after a change such as "+12%!!".

**Why:** Exclamations make every message sound equally urgent and are a strong tell of generated copy.

**How to fix:** Drop the mark; give a change its comparison ("+12% vs last month").

### The title names the page, not the user

`no-greeting-headline` · warning · checked

**Rule:** No "Welcome back, Name" or "Good morning" as the page title of a working screen; the title says what the page shows.

**Why:** A greeting takes the most valuable line on the screen and tells nothing on the hundredth visit.

**How to fix:** Use the page or the period as the title ("Overview · this week").

### Social proof with a source

`no-unsourced-proof` · warning · checked

**Rule:** No "Trusted by 10,000+ teams", rows of five stars or avatar stacks without a source; name the customers or the review site, or leave it out.

**Why:** Round, unsourced numbers are the first thing a visitor stops believing, and they make the rest of the page look invented.

**How to fix:** Show the real number with its source ("4.8 on the App Store, 312 ratings") or a named customer.
