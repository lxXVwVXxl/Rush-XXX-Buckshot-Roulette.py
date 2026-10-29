#!/usr/bin/env python3
"""Buckshot Roulette - text version. Python 3, standard library only."""

import random
import time
from datetime import datetime

# =====================================================================
# CONSTANTS
# =====================================================================
LIVE = "LIVE"      # red shell
BLANK = "BLANK"    # blue shell
SHELL_COLOR = {LIVE: "red", BLANK: "blue"}

MAX_SLOTS = 6                 # max items per side
ITEMS_FROM_STAGE = 2          # items appear only on stage 2 and 3
MAX_STAGE = 3
DEFAULT_LIVES = [3, 4, 6]     # stage 1 / 2 / 3

BEER = "Beer"
MAGNIFIER = "Magnifying glass"
CIGARETTES = "Cigarettes"
HANDSAW = "Handsaw"
HANDCUFFS = "Handcuffs"
PHONE = "Cheap phone"
PILLS = "Pills"
INVERTER = "Inverter"
ITEMS = [BEER, MAGNIFIER, CIGARETTES, HANDSAW, HANDCUFFS, PHONE, PILLS, INVERTER]

FAST = False  # set True to remove delays (used for testing)


def pause(seconds=0.8):
    if not FAST:
        time.sleep(seconds)


def shell_text(shell):
    return f"{SHELL_COLOR[shell].upper()} ({shell})"


# =====================================================================
# SETTINGS
# =====================================================================
def default_settings():
    return {
        "player_lives": DEFAULT_LIVES[:],
        "dealer_lives": DEFAULT_LIVES[:],
        "items": {name: True for name in ITEMS},
        "items_per_load": (1, 4),   # min, max items handed to each side per load
    }


def ask_int(prompt, low, high):
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and low <= int(raw) <= high:
            return int(raw)
        print(f"Enter a number from {low} to {high}.")


def edit_lives(settings, key, label):
    for i in range(MAX_STAGE):
        current = settings[key][i]
        raw = input(f"{label} lives, stage {i + 1} (now {current}, 1-9, Enter = keep): ").strip()
        if raw == "":
            continue
        if raw.isdigit() and 1 <= int(raw) <= 9:
            settings[key][i] = int(raw)
        else:
            print("Ignored (must be 1-9).")


def edit_items(settings):
    while True:
        print("\nItems in game (stage 2 and 3):")
        for i, name in enumerate(ITEMS, 1):
            mark = "x" if settings["items"][name] else " "
            print(f"  {i} - [{mark}] {name}")
        print("  0 - back")
        choice = ask_int("Toggle item: ", 0, len(ITEMS))
        if choice == 0:
            return
        name = ITEMS[choice - 1]
        settings["items"][name] = not settings["items"][name]


def settings_menu(settings):
    while True:
        lo, hi = settings["items_per_load"]
        print("\n=== SETTINGS ===")
        print(f"1 - Player lives per stage: {settings['player_lives']}")
        print(f"2 - Dealer lives per stage: {settings['dealer_lives']}")
        print("3 - Enable / disable items")
        print(f"4 - Items handed out per load: {lo}-{hi}")
        print("5 - Reset to defaults")
        print("6 - Back")
        choice = ask_int("> ", 1, 6)
        if choice == 1:
            edit_lives(settings, "player_lives", "Player")
        elif choice == 2:
            edit_lives(settings, "dealer_lives", "Dealer")
        elif choice == 3:
            edit_items(settings)
        elif choice == 4:
            new_lo = ask_int("Minimum items per load (0-6): ", 0, MAX_SLOTS)
            new_hi = ask_int(f"Maximum items per load ({new_lo}-6): ", new_lo, MAX_SLOTS)
            settings["items_per_load"] = (new_lo, new_hi)
        elif choice == 5:
            settings.clear()
            settings.update(default_settings())
            print("Settings reset.")
        else:
            return


# =====================================================================
# GAME OBJECTS
# =====================================================================
class DealerDead(Exception):
    pass


class PlayerDead(Exception):
    pass


class Side:
    """One participant: the player or the dealer."""

    def __init__(self, name):
        self.name = name
        self.hp = 0
        self.max_hp = 0
        self.items = [None] * MAX_SLOTS
        self.cuffed = False
        self.known = {}   # shell index (0 = current) -> LIVE/BLANK

    def reset_for_stage(self, max_hp):
        self.hp = self.max_hp = max_hp
        self.items = [None] * MAX_SLOTS
        self.cuffed = False
        self.known = {}

    def free_slots(self):
        return [i for i, item in enumerate(self.items) if item is None]

    def has(self, item):
        return item in self.items


class Game:
    def __init__(self, player_name, settings):
        self.settings = settings
        self.player = Side(player_name)
        self.dealer = Side("Dealer")
        self.stage = 1
        self.shells = []
        self.load_live = 0
        self.load_blank = 0
        self.saw = False        # handsaw active for the next shot
        self.holder = "table"   # "table" or a Side

    # ----------------------------------------------------------------
    # helpers
    # ----------------------------------------------------------------
    def other(self, side):
        return self.dealer if side is self.player else self.player

    def check_deaths(self):
        if self.player.hp <= 0:
            raise PlayerDead()
        if self.dealer.hp <= 0:
            raise DealerDead()

    def pop_shell(self):
        shell = self.shells.pop(0)
        for side in (self.player, self.dealer):
            side.known = {i - 1: t for i, t in side.known.items() if i > 0}
        return shell

    # ----------------------------------------------------------------
    # display
    # ----------------------------------------------------------------
    def render(self):
        p, d = self.player, self.dealer
        print("\n" + "=" * 44)
        print(f"Dealer {'i' * d.hp} | stage {self.stage} | {p.name} {'i' * p.hp}")
        print(f"Current load: {self.load_live} red, {self.load_blank} blue")
        print("Shells are loaded in random sequence")
        print("_" * 32)
        if self.holder == "table":
            where = "on table"
        else:
            where = f"in {self.holder.name}'s hands"
        print(f"Shotgun currently {where}")
        if self.saw:
            print("(barrel is sawed off: next LIVE shell deals double damage)")
        if p.cuffed:
            print(f"({p.name} is handcuffed)")
        if d.cuffed:
            print("(Dealer is handcuffed)")
        if p.known:
            parts = [f"shell {i + 1} = {shell_text(t)}" for i, t in sorted(p.known.items())]
            print("You know: " + ", ".join(parts))
        for side in (p, d):
            print(f"\nList of {side.name} items")
            for i, item in enumerate(side.items, 1):
                print(f"{i} {item if item else 'xxx'}")
        print("=" * 44)

    # ----------------------------------------------------------------
    # stage / loading
    # ----------------------------------------------------------------
    def start_stage(self):
        idx = self.stage - 1
        self.player.reset_for_stage(self.settings["player_lives"][idx])
        self.dealer.reset_for_stage(self.settings["dealer_lives"][idx])
        self.shells = []
        self.saw = False
        print(f"\n######## STAGE {self.stage} ########")
        print(f"Lives: {self.player.name} {self.player.max_hp}, Dealer {self.dealer.max_hp}")
        pause()

    def load_shotgun(self):
        total = random.randint(2, 8)
        live = random.randint(1, total - 1)
        blank = total - live
        self.shells = [LIVE] * live + [BLANK] * blank
        random.shuffle(self.shells)
        self.load_live, self.load_blank = live, blank
        self.saw = False
        self.holder = "table"
        for side in (self.player, self.dealer):
            side.known = {}
        print("\nD - Loading the shotgun...")
        pause()
        if self.stage >= ITEMS_FROM_STAGE:
            self.hand_out_items()
        self.render()
        pause()

    def hand_out_items(self):
        enabled = [name for name, on in self.settings["items"].items() if on]
        if not enabled:
            return
        lo, hi = self.settings["items_per_load"]
        amount = random.randint(lo, hi)
        for side in (self.player, self.dealer):
            got = []
            for _ in range(amount):
                free = side.free_slots()
                if not free:
                    break
                item = random.choice(enabled)
                side.items[free[0]] = item
                got.append(item)
            print(f"{side.name} receives: {', '.join(got) if got else 'nothing (no free slots)'}")
        pause()

    # ----------------------------------------------------------------
    # items
    # ----------------------------------------------------------------
    def can_use(self, user, name):
        if name == HANDCUFFS and self.other(user).cuffed:
            return False, "Opponent is already handcuffed."
        if name == HANDSAW and self.saw:
            return False, "The barrel is already sawed off."
        return True, ""

    def use_item(self, user, name):
        slot = user.items.index(name)
        user.items[slot] = None
        opp = self.other(user)
        is_player = user is self.player
        print(f"\n{user.name} uses {name}.")
        pause()

        if name == BEER:
            shell = self.pop_shell()
            print(f"The shotgun ejects a {shell_text(shell)} shell.")

        elif name == MAGNIFIER:
            current = self.shells[0]
            user.known[0] = current
            if is_player:
                print(f"You look into the chamber: {shell_text(current)}")
            else:
                print("Dealer peers into the chamber.")

        elif name == CIGARETTES:
            if user.hp < user.max_hp:
                user.hp += 1
                print(f"{user.name} heals 1 life.")
            else:
                print("Already at full health. No effect.")

        elif name == HANDSAW:
            self.saw = True
            print("Barrel sawed off. Next LIVE shell deals double damage.")

        elif name == HANDCUFFS:
            opp.cuffed = True
            print(f"{opp.name} is handcuffed and will skip the next turn.")

        elif name == PHONE:
            remaining = len(self.shells)
            if remaining < 2:
                print("Phone: ...nothing useful. Only one shell left.")
            else:
                idx = random.randint(1, remaining - 1)   # never the current shell
                user.known[idx] = self.shells[idx]
                if is_player:
                    print(f"Phone: shell number {idx + 1} is {self.shells[idx]}.")
                else:
                    print("Dealer listens to the phone.")

        elif name == PILLS:
            if random.random() < 0.5:
                before = user.hp
                user.hp = min(user.max_hp, user.hp + 2)
                print(f"Pills worked. {user.name} heals {user.hp - before} life.")
            else:
                user.hp -= 1
                print(f"Bad pills! {user.name} loses 1 life.")

        elif name == INVERTER:
            self.shells[0] = BLANK if self.shells[0] == LIVE else LIVE
            for side in (self.player, self.dealer):
                if 0 in side.known:
                    side.known[0] = self.shells[0]
            print("The current shell has been inverted.")

        pause()

    # ----------------------------------------------------------------
    # shooting
    # ----------------------------------------------------------------
    def fire(self, shooter, target):
        shell = self.pop_shell()
        sawn = self.saw
        self.saw = False   # handsaw effect ends after ANY shot
        if shooter is target:
            print(f"\n{shooter.name} points the shotgun at themself...")
        else:
            print(f"\n{shooter.name} points the shotgun at {target.name}...")
        pause(1.2)
        if shell == LIVE:
            dmg = 2 if sawn else 1
            target.hp = max(0, target.hp - dmg)
            print(f"*BANG* - {shell_text(shell)}! {target.name} loses {dmg} life.")
        else:
            print(f"*click* - {shell_text(shell)}. Nothing happens.")
            if sawn:
                print("(the sawed-off effect is wasted)")
        pause()
        return shell

    # ----------------------------------------------------------------
    # choices
    # ----------------------------------------------------------------
    def player_choice(self):
        p = self.player
        self.render()
        print(f"{p.name}, your move:")
        print("  1 - shoot Dealer")
        print("  2 - shoot yourself")
        print("  3 - use item")
        while True:
            choice = ask_int("> ", 1, 3)
            if choice == 1:
                return ("shoot_opp", None)
            if choice == 2:
                return ("shoot_self", None)
            if not any(p.items):
                print("You have no items.")
                continue
            slot = ask_int("Item slot (1-6, 0 = cancel): ", 0, MAX_SLOTS)
            if slot == 0:
                continue
            name = p.items[slot - 1]
            if name is None:
                print("That slot is empty.")
                continue
            ok, why = self.can_use(p, name)
            if not ok:
                print(why)
                continue
            return ("item", name)

    def dealer_choice(self):
        d, p = self.dealer, self.player
        pause(1.0)
        n = len(self.shells)
        live = self.shells.count(LIVE)       # counts are public information
        current = d.known.get(0)

        def can(item):
            return d.has(item) and self.can_use(d, item)[0]

        if current is None and can(MAGNIFIER):
            return ("item", MAGNIFIER)
        if d.hp < d.max_hp and can(CIGARETTES):
            return ("item", CIGARETTES)
        if can(PILLS) and d.hp >= 3 and d.hp <= d.max_hp - 2:
            return ("item", PILLS)
        if can(HANDCUFFS) and n > 1:
            return ("item", HANDCUFFS)
        if can(PHONE) and n > 2 and not d.known:
            return ("item", PHONE)

        if current == LIVE:
            if can(HANDSAW):
                return ("item", HANDSAW)
            return ("shoot_opp", None)
        if current == BLANK:
            if can(INVERTER) and random.random() < 0.5:
                return ("item", INVERTER)
            return ("shoot_self", None)

        # current shell unknown: play the odds
        if can(BEER) and n > 1 and random.random() < 0.5:
            return ("item", BEER)
        if live == n:
            return ("shoot_opp", None)
        if live == 0:
            return ("shoot_self", None)
        chance = live / n
        if chance > 0.5 or (chance == 0.5 and random.random() < 0.5):
            if can(HANDSAW) and random.random() < 0.6:
                return ("item", HANDSAW)
            return ("shoot_opp", None)
        return ("shoot_self", None)

    # ----------------------------------------------------------------
    # turn / main loop
    # ----------------------------------------------------------------
    def take_turn(self, actor):
        opp = self.other(actor)
        self.holder = actor
        while True:
            if actor is self.player:
                kind, arg = self.player_choice()
            else:
                kind, arg = self.dealer_choice()

            if kind == "item":                       # items never end the turn
                self.use_item(actor, arg)
                self.check_deaths()
                if not self.shells:                  # e.g. beer ejected the last shell
                    return
                continue

            target = opp if kind == "shoot_opp" else actor
            shell = self.fire(actor, target)
            self.check_deaths()
            if kind == "shoot_self" and shell == BLANK and self.shells:
                print(f"{actor.name} shot a blank at themself - the turn continues.")
                pause()
                continue
            return                                    # every other shot ends the turn

    def play(self):
        """Run the game. Returns True if the player won."""
        self.stage = 1
        self.start_stage()
        current = self.player
        while True:
            try:
                if not self.shells:                   # shotgun loads only when empty
                    self.load_shotgun()
                    current = self.player             # after a load the player starts
                if current.cuffed:
                    print(f"\n{current.name} is handcuffed and skips the turn. The cuffs break.")
                    current.cuffed = False
                    current = self.other(current)
                    pause()
                    continue
                self.take_turn(current)
                if self.shells:
                    current = self.other(current)
            except DealerDead:
                print("\nD - Dealer is down.")
                self.stage += 1
                if self.stage > MAX_STAGE:
                    print("\n*** You survived all stages. YOU WIN! ***")
                    return True
                print("Health is restored and the next stage begins.")
                pause()
                self.start_stage()
                current = self.player
            except PlayerDead:
                print(f"\n{self.player.name} is dead. GAME OVER.")
                return False


# =====================================================================
# MENU
# =====================================================================
def sign_document():
    print("\n=== DOCUMENT ===")
    while True:
        name = input("Name: ").strip()
        if name:
            break
        print("Name can't be empty.")
    while True:
        surname = input("Surname: ").strip()
        if surname:
            break
        print("Surname can't be empty.")
    print("Document signed.")
    return name, surname


def start_game(signature, settings):
    name, surname = signature
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print("\nD - You have signed document.")
    print(f"Document from {now}, signed by {name} {surname} goes to dealer")
    print("D - Lights out.")
    pause(1.5)
    Game(name, settings).play()


def main():
    settings = default_settings()
    signature = None
    while True:
        print("\n=== BUCKSHOT ROULETTE ===")
        print("1 - Play the roulette")
        print("2 - Sign document" + (f"  (signed: {signature[0]} {signature[1]})" if signature else ""))
        print("3 - Settings")
        print("4 - Exit")
        choice = ask_int("> ", 1, 4)
        if choice == 1:
            if signature is None:
                print("D - No signature, no game. Sign the document first.")
            else:
                start_game(signature, settings)
        elif choice == 2:
            signature = sign_document()
        elif choice == 3:
            settings_menu(settings)
        else:
            print("Bye.")
            return


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")
