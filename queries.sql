SELECT COUNT(*)
FROM PitcherStats;

SELECT *
FROM HitterStats
WHERE `PlayerID` = '444482'; 

TRUNCATE TABLE Contract;

SELECT *
FROM `Team`
WHERE `MLBAffiliateID` IS NULL;

SELECT *
FROM Team
WHERE MLBAffiliateID IS NULL
ORDER BY TeamName;

SELECT hs.*
FROM HitterStats hs
JOIN Team t ON hs.TeamID = t.TeamID
JOIN League l ON t.LeagueID = l.LeagueID
WHERE l.LeagueLevel IN ('Single-A', 'Double-A', 'Triple-A', 'High-A');

SELECT *
FROM `Player`
WHERE `PlayerLevel` = 'Single-A';

SELECT *
FROM `Player`
WHERE FirstName = 'Jared' AND LastName = 'Young';

SELECT *
FROM `HitterStats`
WHERE PlayerID = '676724';

SELECT *
FROM `Team`
WHERE TeamID IN ('105', '112', '235');

SELECT *
FROM `Player`
WHERE FirstName = 'Drew' AND LastName = 'Lugbauer';

SELECT *
FROM `HitterStats`
WHERE PlayerID = '656666';

DELETE hs
FROM HitterStats hs
JOIN Team t ON hs.TeamID = t.TeamID
JOIN League l ON t.LeagueID = l.LeagueID
WHERE hs.Season = 2024
  AND l.LeagueLevel <> 'Major League Baseball';

DELETE ps
FROM `PitcherStats` ps
JOIN Team t ON ps.TeamID = t.TeamID
JOIN League l ON t.LeagueID = l.LeagueID
WHERE ps.Season = 2024
  AND l.LeagueLevel <> 'Major League Baseball';

SELECT hs.*
FROM HitterStats hs
JOIN Team t ON hs.TeamID = t.TeamID
JOIN League l ON t.LeagueID = l.LeagueID
WHERE l.LeagueLevel <> 'Major League Baseball';

SELECT ps.*
FROM PitcherStats ps
JOIN Team t ON ps.TeamID = t.TeamID
JOIN League l ON t.LeagueID = l.LeagueID
WHERE l.LeagueLevel <> 'Major League Baseball';