"""Tracksy – an interactive CLI habit tracker.
Run with ``python main.py``. On start the user logs in (or registers) with a username; all habits are stored per-user in a SQLite database. From the main menu the user can create, complete, inspect, analyse and delete habits.
"""

from datetime import datetime

from db import (
    init_db, save_habit, load_habits, delete_habit,
    create_user, get_user_by_username, add_member, remove_member,
)
from habits.habit import Habit
from analytics.progress import (
    get_all_habit_names, get_habits_by_periodicity, calculate_streak,
    get_habit_with_longest_streak, get_broken_habits, get_period_summary,
    get_member_contributions, completions_in_current_period, get_current_streak,
)
from analytics.visuals import (
    show_completions_by_category, show_completions_by_period,
)

DEFAULT_CATEGORIES = {
    "Health": "💊", "Work": "💼", "Study": "📚",
    "Fitness": "🏋️", "Finance": "💰", "Personal": "🌟",
}
MOOD_EMOJIS = {"1": "😞", "2": "😐", "3": "🙂", "4": "😄", "5": "🤩"}
PERIODICITIES = ["daily", "weekly", "monthly", "yearly"]
PERIODS = {"1": "day", "2": "week", "3": "month", "4": "year"}

current_user = None


# ── Auth ────────────────────────────────────────────────────────────────────

def login_or_register():
    """Log the user in by username, registering them on first use."""
    global current_user
    print("\n👤 Welcome to Tracksy!")
    username = input("Enter your username: ").strip()
    user = get_user_by_username(username)
    if user:
        print(f"\n✅ Welcome back, {user.username}!")
    else:
        print("\n🆕 New user detected. Let's register you!")
        email = input("Enter your email (optional): ").strip() or None
        create_user(username, email)
        user = get_user_by_username(username)
        print(f"✅ Registered successfully. Welcome, {username}!")
    current_user = user


# ── Helpers ─────────────────────────────────────────────────────────────────

def pause_and_return():
    """Wait for Enter before going back to the menu."""
    input("\n✅ Press Enter to return to the menu...")
    print()


def choose_category():
    """Let the user pick a default category or type a custom one."""
    print("\n📂 Choose a category:")
    for i, (cat, emoji) in enumerate(DEFAULT_CATEGORIES.items(), 1):
        print(f"{i}. {emoji} {cat}")
    print(f"{len(DEFAULT_CATEGORIES) + 1}. ➕ Custom")
    choice = input("Select number: ")
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(DEFAULT_CATEGORIES):
            return list(DEFAULT_CATEGORIES.keys())[idx - 1]
        if idx == len(DEFAULT_CATEGORIES) + 1:
            return input("Enter your custom category: ").strip()
    return "Personal"


def show_progress_bar(progress, goal, max_blocks=20):
    """
    Render a compact ■□ progress bar for the current period.
    One block per completion when the goal is small (the usual case, e.g. ``■■■■■□□□ (5/8)``); scaled down to ``max_blocks`` blocks for large goals. 
    Handles habits without a goal and overachievement gracefully.
    """
    if goal:
        if goal <= max_blocks:
            filled, empty = min(progress, goal), max(goal - progress, 0)
        else:
            filled = min(max_blocks, int(max_blocks * progress / goal))
            empty = max_blocks - filled
        if progress > goal:
            status = f", +{progress - goal} extra"
        elif progress == goal:
            status = ", done ✅"
        else:
            status = f", {goal - progress} to go"
        return f"{'■' * filled}{'□' * empty} ({progress}/{goal}{status})"
    return f"{'■' * min(progress, max_blocks)} ({progress}, no goal set)"


def assign_badges(habit):
    """Unlock any new badges for the habit and return the freshly earned ones."""
    new_badges = []

    def unlock(condition, badge):
        """Award the badge once, when its condition is first met."""
        if condition and badge not in habit.badges:
            habit.badges.append(badge)
            new_badges.append(badge)

    streak = calculate_streak(habit)
    unlock(habit.progress >= 1, "🏁 First Step")
    unlock(streak >= 3, "🔁 3-Period Streak")
    unlock(streak >= 7, "🔥 7-Period Streak")
    unlock(habit.goal and completions_in_current_period(habit) >= habit.goal,
           "🏆 Goal Reached")
    return new_badges


# ── Habit management ────────────────────────────────────────────────────────

def create_habit():
    """Interactively create a new habit for the current user."""
    print("\n🛠️ Create a new habit")
    name = input("Name your habit: ").strip()
    if not name:
        print("❌ Name cannot be empty.")
        pause_and_return()
        return

    existing = load_habits(current_user.user_id)
    if any(h.name == name for h in existing):
        print("⚠️ You already have a habit with that name.")
        pause_and_return()
        return

    print("\n📅 Choose periodicity:")
    for i, p in enumerate(PERIODICITIES, 1):
        print(f"{i}. {p.capitalize()}")
    p_choice = input("Choose number: ")
    periodicity = (PERIODICITIES[int(p_choice) - 1]
                   if p_choice.isdigit() and 1 <= int(p_choice) <= len(PERIODICITIES)
                   else "daily")

    category = choose_category()
    goal = input(f"🎯 Times to complete per {periodicity} period? (optional): ").strip()
    goal = int(goal) if goal.isdigit() else None

    habit = Habit(name=name, periodicity=periodicity, category=category, goal=goal)
    save_habit(habit, current_user.user_id)
    print(f"\n✅ Habit '{habit.name}' created!")
    pause_and_return()


def shared_label(habit):
    """Return a '🤝 shared with: ...' suffix for shared habits, else ''."""
    if not habit.shared:
        return ""
    others = [n for i, n in zip(habit.member_ids, habit.member_names)
              if i != current_user.user_id]
    return f" 🤝 shared with: {', '.join(others)}"


PERIOD_WORD = {"daily": "today", "weekly": "this week",
               "monthly": "this month", "yearly": "this year"}
PERIOD_NOUN = {"daily": "day", "weekly": "week",
               "monthly": "month", "yearly": "year"}


def show_all_habits():
    """
    List all habits with their progress bar for the current period.
    The bar compares check-offs in the habit's *current* period against the per-period goal (e.g. 4 of 5 glasses of water today); the flame shows the live streak in consecutive periods.
    """
    habits = load_habits(current_user.user_id)
    if not habits:
        print("\n📭 No habits found.")
    else:
        print("\n📋 Your Tracked Habits:")
        for h in habits:
            done_now = completions_in_current_period(h)
            streak = get_current_streak(h)
            noun = PERIOD_NOUN.get(h.periodicity, "period")
            flame = f" 🔥 {streak}-{noun} streak" if streak else ""
            when = PERIOD_WORD.get(h.periodicity, "now")
            print(f"\n• {h.name} ({h.periodicity}){shared_label(h)}{flame}")
            print(f"  {show_progress_bar(done_now, h.goal)} {when}")
    pause_and_return()


def track_habit_progress():
    """Check off a habit's task and update badges/mood."""
    habits = load_habits(current_user.user_id)
    if not habits:
        print("\n⚠️ No habits to track.")
        pause_and_return()
        return

    print("\n🎯 Select a habit to update:")
    for i, h in enumerate(habits, 1):
        done_now = completions_in_current_period(h)
        print(f"{i}. {h.name} ({h.periodicity}) - "
              f"{done_now}/{h.goal or '-'} {PERIOD_WORD.get(h.periodicity, '')}")
    choice = input("Enter number: ")
    if not choice.isdigit() or not (1 <= int(choice) <= len(habits)):
        print("❌ Invalid.")
        pause_and_return()
        return

    habit = habits[int(choice) - 1]
    habit.complete(user_id=current_user.user_id)
    done_now = completions_in_current_period(habit)
    print(show_progress_bar(done_now, habit.goal))
    for badge in assign_badges(habit):
        print(f"🎖️ Badge Unlocked: {badge}")
    if habit.goal and done_now >= habit.goal:
        mood = input("🧠 Goal completed! How do you feel (1–5)? ").strip()
        if mood in MOOD_EMOJIS:
            habit.mood[datetime.now().isoformat()] = MOOD_EMOJIS[mood]
            print(f"🧠 Mood saved: {MOOD_EMOJIS[mood]}")
    save_habit(habit, current_user.user_id)
    pause_and_return()


def share_habit():
    """
    Share one of the user's habits with another registered user.
    Any member of a habit can add further members; a habit with 2+ membersbecomes a shared habit (e.g. household chores).
    """
    habits = load_habits(current_user.user_id)
    if not habits:
        print("\n📭 No habits to share.")
        pause_and_return()
        return

    print("\n🤝 Which habit do you want to share?")
    for i, h in enumerate(habits, 1):
        print(f"{i}. {h.name}{shared_label(h)}")
    choice = input("Choose number: ")
    if not choice.isdigit() or not (1 <= int(choice) <= len(habits)):
        print("❌ Invalid selection.")
        pause_and_return()
        return
    habit = habits[int(choice) - 1]

    username = input("Enter the username to share with: ").strip()
    other = get_user_by_username(username)
    if other is None:
        print(f"❌ User '{username}' not found. They must register first "
              "(just log in once with their username).")
    elif other.user_id in habit.member_ids:
        print(f"ℹ️ '{habit.name}' is already shared with {username}.")
    else:
        add_member(habit.habit_id, other.user_id)
        print(f"✅ '{habit.name}' is now shared with {username}!")
    pause_and_return()


def delete_habit_cli():
    """Delete a habit — for everyone if private, only for me if shared."""
    habits = load_habits(current_user.user_id)
    if not habits:
        print("\n📭 No habits to delete.")
        pause_and_return()
        return

    print("\n🗑️ Choose habit to delete:")
    for i, habit in enumerate(habits, 1):
        print(f"{i}. {habit.name}")
    choice = input("Choose number: ")
    if not choice.isdigit() or not (1 <= int(choice) <= len(habits)):
        print("❌ Invalid selection.")
        pause_and_return()
        return

    selected = habits[int(choice) - 1]
    if selected.shared:
        prompt = (f"'{selected.name}' is shared{shared_label(selected)}.\n"
                  "Remove it only for you (the others keep it)? (y/n): ")
    else:
        prompt = f"Delete '{selected.name}'? (y/n): "

    if input(prompt).lower() == "y":
        if selected.shared:
            remove_member(selected.habit_id, current_user.user_id)
            print(f"✅ Removed for you: {selected.name}")
        else:
            delete_habit(selected.habit_id)
            print(f"✅ Deleted: {selected.name}")
    else:
        print("❎ Cancelled.")
    pause_and_return()


# ── Mood & badges ───────────────────────────────────────────────────────────

def show_all_moods():
    """Print the mood history recorded across all habits."""
    habits = load_habits(current_user.user_id)
    print("\n🧠 Mood history:")
    for h in habits:
        if h.mood:
            print(f"\n📌 {h.name}:")
            for d, r in h.mood.items():
                print(f"{d}: {r}")
    pause_and_return()


def show_badges():
    """Print all unlocked badges grouped by habit."""
    habits = load_habits(current_user.user_id)
    print("\n🎖️ Your Unlocked Badges:")
    found = False
    for h in habits:
        if h.badges:
            found = True
            print(f"\n🏷️ {h.name} ({h.periodicity})")
            for b in h.badges:
                print(f" - {b}")
    if not found:
        print("📭 No badges yet.")
    pause_and_return()


# ── Analytics ───────────────────────────────────────────────────────────────

def analytics_menu():
    """Interactive sub-menu exposing the analytics module."""
    while True:
        habits = load_habits(current_user.user_id)
        print("\n📊 Analytics Menu")
        print("1. All habit names")
        print("2. Habits by periodicity")
        print("3. Longest streak of all habits")
        print("4. Longest streak for one habit")
        print("5. Broken habits")
        print("6. Completions in the current day/week/month/year (all habits)")
        print("7. 👥 Member contributions (shared habits)")
        print("8. 📊 Visualize completions by category")
        print("9. 📈 Visualize completions by period")
        print("10. 🔙 Back to menu")
        ch = input("Select: ")
        if ch == "1":
            for name in get_all_habit_names(habits):
                print(f"- {name}")
        elif ch == "2":
            for i, p in enumerate(PERIODICITIES, 1):
                print(f"{i}. {p.capitalize()}")
            p_choice = input("Choose: ")
            if p_choice.isdigit() and 1 <= int(p_choice) <= len(PERIODICITIES):
                per = PERIODICITIES[int(p_choice) - 1]
                for h in get_habits_by_periodicity(habits, per):
                    print(f"- {h.name}")
        elif ch == "3":
            habit, streak = get_habit_with_longest_streak(habits)
            if habit:
                print(f"🔥 {habit.name}: {streak} {habit.periodicity} periods")
        elif ch == "4":
            for i, h in enumerate(habits, 1):
                print(f"{i}. {h.name}")
            ch2 = input("Select: ")
            if ch2.isdigit() and 1 <= int(ch2) <= len(habits):
                habit = habits[int(ch2) - 1]
                print(f"🔥 {habit.name}: {calculate_streak(habit)} "
                      f"{habit.periodicity} periods")
        elif ch == "5":
            broken = get_broken_habits(habits)
            if not broken:
                print("🎉 No broken habits!")
            for h in broken:
                print(f"❌ {h.name}")
        elif ch == "6":
            print("1. Day 2. Week 3. Month 4. Year")
            period = PERIODS.get(input("Choose: "))
            if period:
                print(f"\n📆 Check-offs of all habits in the current {period}:")
                for name, c in get_period_summary(habits, period):
                    print(f"- {name}: {c}")
        elif ch == "7":
            shared = [h for h in habits if h.shared]
            if not shared:
                print("📭 No shared habits yet.")
            for i, h in enumerate(shared, 1):
                print(f"{i}. {h.name}{shared_label(h)}")
            if shared:
                ch2 = input("Select: ")
                if ch2.isdigit() and 1 <= int(ch2) <= len(shared):
                    habit = shared[int(ch2) - 1]
                    names = dict(zip(habit.member_ids, habit.member_names))
                    print(f"\n📊 Contributions for '{habit.name}':")
                    for uid, count in get_member_contributions(habit):
                        print(f"- {names.get(uid, f'user {uid}')}: {count}")
        elif ch == "8":
            show_completions_by_category(habits)
        elif ch == "9":
            print("1. Day 2. Week 3. Month 4. Year")
            period = PERIODS.get(input("Choose: "))
            if period:
                show_completions_by_period(habits, period)
        elif ch == "10":
            break
        pause_and_return()


# ── Main loop ───────────────────────────────────────────────────────────────

def welcome_flow():
    """Login, then loop over the main menu until the user exits."""
    login_or_register()
    while True:
        print("\n🌟 What do you want to do?")
        print("1. ➕ Create habit")
        print("2. ✅ Track progress")
        print("3. 📋 Show habits")
        print("4. 🤝 Share habit")
        print("5. 📊 Analytics")
        print("6. 💪 Show mood history")
        print("7. 🎖️ Show badges")
        print("8. 🗑️ Delete habit")
        print("9. 👋 Exit")
        ch = input("Select: ")
        if ch == "1":
            create_habit()
        elif ch == "2":
            track_habit_progress()
        elif ch == "3":
            show_all_habits()
        elif ch == "4":
            share_habit()
        elif ch == "5":
            analytics_menu()
        elif ch == "6":
            show_all_moods()
        elif ch == "7":
            show_badges()
        elif ch == "8":
            delete_habit_cli()
        elif ch == "9":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid.")


if __name__ == "__main__":
    init_db()
    welcome_flow()
