
create table LamsMainCommits (
    CommitHash VARCHAR(10),
    Author VARCHAR(100),
    AuthorDate TIMESTAMP,
    CommitMessage VARCHAR(4000),
    FileChangeCounts VARCHAR(100)
)

COPY LamsMainCommits
FROM '/Volumes/pdf_files/garf/Kris/Projects/LamsGitCommitReport_20241120/LamsMainCommits.csv'
WITH CSV HEADER;

CREATE TABLE LamsTimeSheets (
    Consultant VARCHAR(255),
    Date DATE,
    DescriptioDn VARCHAR(4000)
);

SELECT CommitsSub.WeekStartingOn,
    NumberOfCommits,
    LineChanges,
    FilesChanged,
    NumberOfCommitAuthors,
    NumberOfConsultantsOnTimeSheets,
    CommitMessages,
    TimeSheetDescriptions
FROM (
    SELECT CommitsSubSub.WeekStartingOn,
        COUNT(*) AS NumberOfCommits,
        SUM(COALESCE(Insertions, 0) + COALESCE(Deletions, 0)) AS LineChanges,
        SUM(FilesChanged) AS FilesChanged,
        COUNT(DISTINCT(Author)) AS NumberOfCommitAuthors,
        array_to_string( array_agg( DISTINCT CommitMessage ), ' ' ) AS CommitMessages
    FROM (
        SELECT TO_CHAR(DATE_TRUNC('week', AuthorDate), 'MM/DD/YYYY') AS WeekStartingOn,
            UNNEST(REGEXP_MATCHES(FileChangeCounts, '^(\d*) file.*'))::DECIMAL AS FilesChanged,
            NULLIF(UNNEST(REGEXP_MATCHES(FileChangeCounts, '.* (\d*) insertion.*')), '')::DECIMAL AS Insertions,
            NULLIF(UNNEST(REGEXP_MATCHES(FileChangeCounts, '.* (\d*) deletion.*')), '')::DECIMAL AS Deletions,
            *
        FROM LamsMainCommits
    ) CommitsSubSub
    GROUP BY CommitsSubSub.WeekStartingOn
) CommitsSub
LEFT JOIN (
    SELECT TO_CHAR(DATE_TRUNC('week', Date), 'MM/DD/YYYY') AS WeekStartingOn,
        array_to_string( array_agg( DISTINCT Description ), ' ' ) AS TimeSheetDescriptions,
        COUNT(DISTINCT(Consultant)) AS NumberOfConsultantsOnTimeSheets
    FROM LamsTimeSheets
    GROUP BY TO_CHAR(DATE_TRUNC('week', Date), 'MM/DD/YYYY')
) TimeSheetsSub ON CommitsSub.WeekStartingOn = TimeSheetsSub.WeekStartingOn
ORDER BY CommitsSub.WeekStartingOn::DATE DESC;

SELECT *
FROM LamsTimeSheets;