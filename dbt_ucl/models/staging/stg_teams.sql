-- ================================================================
-- Model   : stg_teams
-- Layer   : Staging
-- Source  : data/silver_local/teams_silver_ucl_teams_*.parquet
-- Purpose : UCL team dimension table.
--           Mart models join to this for team metadata enrichment.
-- ================================================================

with source as (
    select *
    from read_parquet("../data/silver_local/teams_silver_ucl_teams_*.parquet")
),

staged as (

    select
        --Team info
        team_id,
        team_name,
        team_short_name,
        team_tla,
        team_display_name,

        --Club details 
        founded_year,
        club_colours,
        venue_name,
        website,

        --Country / area 
        area_id,
        area_name,
        area_code,

        --Competition context 
        competition_id,
        competition_name,
        competition_code,
        is_ucl_participant,

        --metadata 
        silver_processed_at,
        source_blob

    from source

)

select * from staged