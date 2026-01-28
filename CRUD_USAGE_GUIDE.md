# Player CRUD Operations - Usage Examples

## Quick Start Guide

### Running the Application
```bash
cd c:\Users\Pteta\MLBScoutingProject-main\MLBScoutingProject-main
C:/Python313/python.exe -m streamlit run 07_mlb_assistant_app.py
```

Then navigate to: **http://localhost:8501**

## UI-Based Usage (Via Streamlit)

### 1. CREATE - Adding a New Player

**Steps:**
1. Navigate to: **Player Management (CRUD)** → **Create New Player**
2. Fill in the form:
   - **First Name:** John (required)
   - **Last Name:** Doe (required)
   - **Date of Birth:** Select a date (optional)
   - **Position:** Select from dropdown (C, 1B, 2B, 3B, SS, LF, CF, RF, DH, UT, P, etc.)
   - **Height:** Enter height in inches (optional)
   - **Weight:** Enter weight in pounds (optional)
   - **Throws:** L or R (optional)
   - **Bats:** L, R, or S (optional)
   - **Player Level:** MLB, MiLB, College, International, or High School (optional)
3. Click **"Create Player"** button
4. Success message displays with assigned Player ID

**Example:**
```
First Name: Mike
Last Name: Trout
Position: CF
Height: 71
Weight: 215
Throws: R
Bats: R
Player Level: MLB
→ Player created successfully! Player ID: 42
```

---

### 2. READ - Viewing All Players

**Steps:**
1. Navigate to: **Player Management (CRUD)** → **View Players**
2. Displays:
   - Total player count in database
   - Paginated list of players
3. Use controls:
   - **Players per page:** Choose 10, 25, 50, or 100
   - **Page number:** Navigate between pages
4. Table shows all player information in a formatted display

**Example Output:**
| PlayerID | FirstName | LastName | DateOfBirth | Position | Height | Weight | Throws | Bats | PlayerLevel |
|----------|-----------|----------|-------------|----------|--------|--------|--------|------|-------------|
| 1 | Mike | Trout | 1991-08-27 | CF | 71 | 215 | R | R | MLB |
| 2 | Clayton | Kershaw | 1987-03-19 | P | 73 | 225 | L | L | MLB |

---

### 3. SEARCH - Finding Specific Players

**Steps:**
1. Navigate to: **Player Management (CRUD)** → **Search Player**
2. Enter search term (first name, last name, or partial match)
3. View search results table
4. Click dropdown to select a player
5. View full details of selected player

**Search Examples:**
- Search: "Trout" → Returns all players with "Trout" in first or last name
- Search: "Joh" → Returns "John Doe", "John Smith", etc.
- Search: "M" → Returns all players with "M" in their name

**Example Output:**
```
Enter player name: "Smith"
Found 3 player(s)

Results displayed in table with columns:
PlayerID, FirstName, LastName, DateOfBirth, Position, Height, Weight, Throws, Bats, PlayerLevel

Selected: John Smith (ID: 45)

Details for John Smith:
- Player ID: 45
- Position: SS
- Height (in): 74
- Weight (lbs): 200
- Date of Birth: 1992-05-15
- Throws: R
- Bats: R
- Player Level: MLB
```

---

### 4. UPDATE - Modifying Player Information

**Steps:**
1. Navigate to: **Player Management (CRUD)** → **Update Player**
2. Search for player by name
3. Select player from dropdown
4. Edit fields in the form (pre-populated with current values)
5. Only changed fields will be updated
6. Click **"Update Player"** button
7. Success confirmation message

**Example:**
```
Updating: Mike Trout

Original values → Updated values:
- Position: CF → RF
- Weight: 215 → 217
- Height: 71 → 71 (unchanged)

→ Player updated successfully!
```

---

### 5. DELETE - Removing Players

**Steps:**
1. Navigate to: **Player Management (CRUD)** → **Delete Player**
2. ⚠️ Review warning about cascading effects
3. Search for player by name
4. Select player from dropdown
5. **Important:** Check confirmation checkbox
6. Click **"🗑️ Delete Player"** button
7. Player record is permanently deleted

**Safety Features:**
- Warning about cascading effects
- Confirmation checkbox required
- Player details displayed before deletion
- Soft delete option (consider adding in future)

**Example:**
```
⚠️ Warning: This action cannot be undone! Deleting a player may have 
cascading effects on related records (stats, contracts, etc.)

Confirm deletion of: John Doe (ID: 45)
☑ I confirm I want to delete John Doe

[🗑️ Delete Player]

→ Player deleted successfully!
```

---

## Programmatic Usage (Python)

If you want to use the CRUD operations directly in Python code:

```python
from player_crud import PlayerCRUD
import mysql.connector

# Database connection
config = {
    'host': 'your_host',
    'user': 'your_user',
    'password': 'your_password',
    'database': 'your_database',
    'port': 25060
}

conn = mysql.connector.connect(**config)
crud = PlayerCRUD(conn)

# CREATE
print("Creating new player...")
player_id = crud.create_player(
    first_name="Juan",
    last_name="Soto",
    date_of_birth="1998-10-25",
    position="RF",
    height=72,
    weight=210,
    throws="R",
    bats="L",
    player_level="MLB"
)
print(f"Created player with ID: {player_id}")

# READ single player
print("\nReading player...")
player = crud.read_player(player_id)
if player:
    print(f"Player: {player['FirstName']} {player['LastName']}")
    print(f"Position: {player['Position']}")
    print(f"Level: {player['PlayerLevel']}")

# READ all players (with pagination)
print("\nReading first 5 players...")
players = crud.read_all_players(limit=5, offset=0)
for player in players:
    print(f"  - {player['FirstName']} {player['LastName']} ({player['Position']})")

# SEARCH
print("\nSearching for players...")
results = crud.search_players("Soto")
for player in results:
    print(f"  - {player['FirstName']} {player['LastName']} (ID: {player['PlayerID']})")

# UPDATE
print("\nUpdating player...")
success = crud.update_player(
    player_id,
    position="DH",
    weight=215
)
if success:
    print("Player updated successfully!")
    updated_player = crud.read_player(player_id)
    print(f"New position: {updated_player['Position']}")
    print(f"New weight: {updated_player['Weight']}")

# DELETE
print("\nDeleting player...")
success = crud.delete_player(player_id)
if success:
    print(f"Player {player_id} deleted successfully!")

# Get total count
print("\nTotal players in database:")
count = crud.get_player_count()
print(f"  {count} players")

conn.close()
```

---

## Error Handling

All CRUD operations include built-in error handling:

```
Database error creating player: ...
Database error reading player: ...
Database error updating player: ...
Database error deleting player: ...
Error creating player: ...
Error reading player: ...
```

These messages appear as red error boxes in the Streamlit UI.

---

## Field Reference

### Player Table Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| PlayerID | INT | Auto-generated | Primary Key |
| FirstName | VARCHAR(100) | Yes | Player's first name |
| LastName | VARCHAR(100) | Yes | Player's last name |
| DateOfBirth | DATE | No | Format: YYYY-MM-DD |
| Position | VARCHAR(50) | No | Examples: C, 1B, 2B, 3B, SS, OF, P |
| Height | INT | No | Height in inches |
| Weight | INT | No | Weight in pounds |
| Throws | VARCHAR(5) | No | 'L' for Left, 'R' for Right |
| Bats | VARCHAR(5) | No | 'L' for Left, 'R' for Right, 'S' for Switch |
| PlayerLevel | VARCHAR(50) | No | Examples: MLB, MiLB, College, International |

---

## Tips & Best Practices

1. **Search Before Update/Delete:** Always search to confirm you have the right player before making changes.

2. **Use Pagination:** For databases with many players, use pagination (View Players) to avoid loading too much data at once.

3. **Backup Important Data:** Before bulk deletions, ensure you have backups of important records.

4. **Verify Relationships:** Note that deleting a player might affect related tables (HitterStats, PitcherStats, Contract).

5. **Use Consistent Position Codes:** Refer to the POSITION_CODE_TO_FULL mapping for standard position codes.

6. **Date Format:** Always use YYYY-MM-DD format for dates (the UI handles this automatically).

---

## Troubleshooting

**Problem:** "Database connection failed"
- Solution: Check your .env file has correct DB credentials

**Problem:** "No player found with ID {id}"
- Solution: Verify the player ID exists using the Search or View Players function

**Problem:** Player record won't delete
- Solution: Check if there are related records in HitterStats, PitcherStats, or Contract tables

**Problem:** Update shows "No changes detected"
- Solution: Ensure you modified at least one field from the original values

---

## Additional Notes

- The Player CRUD module is completely separate and doesn't interfere with existing functionality
- All operations use parameterized queries for security (SQL injection prevention)
- The application maintains transaction integrity with proper commit/rollback handling
- All user inputs are properly validated before database operations
