--
-- PostgreSQL database dump
--

\restrict rbHPrFuMmrucJid4cS0vewt4cW99e1afpQbqEjajEPjNgBr3emGeZHLmEmq1lU8

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA extensions;


--
-- Name: graphql; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA graphql;


--
-- Name: library; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA library;


--
-- Name: pgbouncer; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA pgbouncer;


--
-- Name: plans; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA plans;


--
-- Name: profile; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA profile;


--
-- Name: system; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA system;


--
-- Name: tracker; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA tracker;


--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA vault;


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;


--
-- Name: EXTENSION supabase_vault; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION supabase_vault IS 'Supabase Vault Extension';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: grant_pg_cron_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_cron_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_cron'
  )
  THEN
    grant usage on schema cron to postgres with grant option;

    alter default privileges in schema cron grant all on tables to postgres with grant option;
    alter default privileges in schema cron grant all on functions to postgres with grant option;
    alter default privileges in schema cron grant all on sequences to postgres with grant option;

    alter default privileges for user supabase_admin in schema cron grant all
        on sequences to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on tables to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on functions to postgres with grant option;

    grant all privileges on all tables in schema cron to postgres with grant option;
    revoke all on table cron.job from postgres;
    grant select on table cron.job to postgres with grant option;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_cron_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_cron_access() IS 'Grants access to pg_cron';


--
-- Name: grant_pg_graphql_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_graphql_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
begin
    if not exists (
        select 1
        from pg_event_trigger_ddl_commands() ev
        join pg_catalog.pg_extension e on ev.objid = e.oid
        where e.extname = 'pg_graphql'
    ) then
        return;
    end if;

    drop function if exists graphql_public.graphql;
    create or replace function graphql_public.graphql(
        "operationName" text default null,
        query text default null,
        variables jsonb default null,
        extensions jsonb default null
    )
        returns jsonb
        language sql
    as $$
        select graphql.resolve(
            query := query,
            variables := coalesce(variables, '{}'),
            "operationName" := "operationName",
            extensions := extensions
        );
    $$;

    -- Attach the wrapper to the extension so DROP EXTENSION cascades to it,
    -- which in turn triggers set_graphql_placeholder to reinstall the "not enabled" stub.
    alter extension pg_graphql add function graphql_public.graphql(text, text, jsonb, jsonb);

    grant usage on schema graphql to postgres, anon, authenticated, service_role;
    grant execute on function graphql.resolve to postgres, anon, authenticated, service_role;
    grant usage on schema graphql to postgres with grant option;
    grant usage on schema graphql_public to postgres with grant option;
end;
$_$;


--
-- Name: FUNCTION grant_pg_graphql_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_graphql_access() IS 'Grants access to pg_graphql';


--
-- Name: grant_pg_net_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_net_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_net'
  )
  THEN
    IF NOT EXISTS (
      SELECT 1
      FROM pg_roles
      WHERE rolname = 'supabase_functions_admin'
    )
    THEN
      CREATE USER supabase_functions_admin NOINHERIT CREATEROLE LOGIN NOREPLICATION;
    END IF;

    GRANT USAGE ON SCHEMA net TO supabase_functions_admin, postgres, anon, authenticated, service_role;

    IF EXISTS (
      SELECT FROM pg_extension
      WHERE extname = 'pg_net'
      -- all versions in use on existing projects as of 2025-02-20
      -- version 0.12.0 onwards don't need these applied
      AND extversion IN ('0.2', '0.6', '0.7', '0.7.1', '0.8', '0.10.0', '0.11.0')
    ) THEN
      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;

      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;

      REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;
      REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

      GRANT EXECUTE ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
      GRANT EXECUTE ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
    END IF;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_net_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_net_access() IS 'Grants access to pg_net';


--
-- Name: pgrst_ddl_watch(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.pgrst_ddl_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN SELECT * FROM pg_event_trigger_ddl_commands()
  LOOP
    IF cmd.command_tag IN (
      'CREATE SCHEMA', 'ALTER SCHEMA'
    , 'CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO', 'ALTER TABLE'
    , 'CREATE FOREIGN TABLE', 'ALTER FOREIGN TABLE'
    , 'CREATE VIEW', 'ALTER VIEW'
    , 'CREATE MATERIALIZED VIEW', 'ALTER MATERIALIZED VIEW'
    , 'CREATE FUNCTION', 'ALTER FUNCTION'
    , 'CREATE TRIGGER'
    , 'CREATE TYPE', 'ALTER TYPE'
    , 'CREATE RULE'
    , 'COMMENT'
    )
    -- don't notify in case of CREATE TEMP table or other objects created on pg_temp
    AND cmd.schema_name is distinct from 'pg_temp'
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: pgrst_drop_watch(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.pgrst_drop_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects()
  LOOP
    IF obj.object_type IN (
      'schema'
    , 'table'
    , 'foreign table'
    , 'view'
    , 'materialized view'
    , 'function'
    , 'trigger'
    , 'type'
    , 'rule'
    )
    AND obj.is_temporary IS false -- no pg_temp objects
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: set_graphql_placeholder(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.set_graphql_placeholder() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
    DECLARE
    graphql_is_dropped bool;
    BEGIN
    graphql_is_dropped = (
        SELECT ev.schema_name = 'graphql_public'
        FROM pg_event_trigger_dropped_objects() AS ev
        WHERE ev.schema_name = 'graphql_public'
    );

    IF graphql_is_dropped
    THEN
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language plpgsql
        as $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;
    END IF;

    END;
$_$;


--
-- Name: FUNCTION set_graphql_placeholder(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.set_graphql_placeholder() IS 'Reintroduces placeholder function for graphql_public.graphql';


--
-- Name: get_auth(text); Type: FUNCTION; Schema: pgbouncer; Owner: -
--

CREATE FUNCTION pgbouncer.get_auth(p_usename text) RETURNS TABLE(username text, password text)
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO ''
    AS $_$
  BEGIN
      RAISE DEBUG 'PgBouncer auth request: %', p_usename;

      RETURN QUERY
      SELECT
          rolname::text,
          CASE WHEN rolvaliduntil < now()
              THEN null
              ELSE rolpassword::text
          END
      FROM pg_authid
      WHERE rolname=$1 and rolcanlogin;
  END;
  $_$;


--
-- Name: handle_new_user(); Type: FUNCTION; Schema: profile; Owner: -
--

CREATE FUNCTION profile.handle_new_user() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
  INSERT INTO profile.users (id, full_name, role)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'full_name',
    COALESCE(NEW.raw_user_meta_data->>'role', 'general')
  );
  RETURN NEW;
END;
$$;


--
-- Name: get_user_nutrition_stats(uuid, date, date); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_user_nutrition_stats(u_id uuid, start_date date, end_date date) RETURNS TABLE(total_protein numeric, total_calories bigint, total_carbs numeric, total_fat numeric, total_sodium numeric)
    LANGUAGE sql
    AS $$
    SELECT 
        COALESCE(SUM(n.protein_g), 0),
        COALESCE(SUM(n.calories_cal), 0),
        COALESCE(SUM(n.carbohydrates_g), 0),
        COALESCE(SUM(n.total_fat_g), 0),
        COALESCE(SUM(n.sodium_mg), 0)
    FROM tracker.user_meal_schedule s
    JOIN library.meal_nutrition n ON s.meal_id = n.meal_id
    WHERE s.user_id = u_id
      AND s.is_eaten = true
      AND s.scheduled_date >= start_date 
      AND s.scheduled_date <= end_date;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: Exercises; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library."Exercises" (
    "ExerciseId" integer NOT NULL,
    "ExerciseCode" character varying(8) NOT NULL,
    "Name" character varying(200) NOT NULL,
    "Priority" smallint NOT NULL,
    "TargetMuscle" character varying(100) NOT NULL,
    "ExerciseType" character varying(50) NOT NULL,
    "EquipmentCategory" character varying(50) NOT NULL,
    "MediaUrl" character varying(500),
    "MediaType" character varying(20),
    "ThumbnailUrl" character varying(500),
    "ManualTag" character varying(200),
    "Instructions" character varying,
    "IsCustom" boolean NOT NULL,
    "IsArchived" boolean NOT NULL,
    "IsBodyweightOnly" boolean NOT NULL,
    "WorkoutCategory" character varying(20) NOT NULL,
    "CreatedAt" timestamp without time zone NOT NULL,
    "UpdatedAt" timestamp without time zone NOT NULL
);


--
-- Name: Exercises_ExerciseId_seq; Type: SEQUENCE; Schema: library; Owner: -
--

CREATE SEQUENCE library."Exercises_ExerciseId_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: Exercises_ExerciseId_seq; Type: SEQUENCE OWNED BY; Schema: library; Owner: -
--

ALTER SEQUENCE library."Exercises_ExerciseId_seq" OWNED BY library."Exercises"."ExerciseId";


--
-- Name: condition_food_filters; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.condition_food_filters (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    condition_id uuid NOT NULL,
    filter_type character varying NOT NULL,
    token character varying NOT NULL,
    note text,
    CONSTRAINT condition_food_filters_filter_type_check CHECK (((filter_type)::text = ANY ((ARRAY['exclude_ingredient'::character varying, 'exclude_tag'::character varying, 'require_label'::character varying])::text[])))
);


--
-- Name: condition_nutrition_rules; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.condition_nutrition_rules (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    condition_id uuid NOT NULL,
    metric character varying NOT NULL,
    operator character varying(5) NOT NULL,
    value numeric(10,4) NOT NULL,
    priority character varying DEFAULT 'default'::character varying NOT NULL,
    scope character varying DEFAULT 'per_day'::character varying NOT NULL,
    note text,
    CONSTRAINT condition_nutrition_rules_operator_check CHECK (((operator)::text = ANY ((ARRAY['<'::character varying, '<='::character varying, '>'::character varying, '>='::character varying])::text[]))),
    CONSTRAINT condition_nutrition_rules_priority_check CHECK (((priority)::text = ANY ((ARRAY['default'::character varying, 'strict_optional'::character varying, 'default_no_diabetes'::character varying, 'default_with_diabetes'::character varying, 'default_with_diabetes_low'::character varying, 'default_with_diabetes_high'::character varying])::text[]))),
    CONSTRAINT condition_nutrition_rules_scope_check CHECK (((scope)::text = ANY ((ARRAY['per_day'::character varying, 'per_serving'::character varying, 'per_eating_occasion'::character varying, 'pct_energy'::character varying, 'per_kg_per_day'::character varying])::text[])))
);


--
-- Name: conditions; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.conditions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    code character varying(50) NOT NULL,
    display_name character varying NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: exercise_secondary_muscles; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.exercise_secondary_muscles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    exercise_id uuid NOT NULL,
    muscle_name character varying NOT NULL
);


--
-- Name: exercises; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.exercises (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source_id character varying,
    title character varying NOT NULL,
    exercise_type character varying,
    muscle_group character varying,
    equipment_category character varying,
    url text,
    media_type character varying,
    thumbnail_url text,
    instructions text,
    manual_tag character varying,
    priority integer DEFAULT 0,
    is_custom boolean DEFAULT false NOT NULL,
    is_archived boolean DEFAULT false NOT NULL,
    hundred_percent_bodyweight boolean DEFAULT false NOT NULL
);


--
-- Name: ingredients; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.ingredients (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    meal_id uuid NOT NULL,
    description text NOT NULL
);


--
-- Name: meal_nutrition; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.meal_nutrition (
    meal_id uuid NOT NULL,
    calories_cal integer,
    kilojoules_kj integer,
    protein_g numeric(6,2),
    total_fat_g numeric(6,2),
    carbohydrates_g numeric(6,2),
    sugar_g numeric(6,2),
    saturated_fat_g numeric,
    dietary_fibre_g numeric,
    sodium_mg numeric,
    calcium_mg numeric,
    iron_mg numeric
);


--
-- Name: meal_tags; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.meal_tags (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    meal_id uuid NOT NULL,
    tag_name character varying(100) NOT NULL
);


--
-- Name: meals; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.meals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title character varying NOT NULL,
    url text,
    image_url text,
    servings integer,
    prep_time character varying(50),
    time_to_make character varying(50),
    instructions jsonb,
    guide_info text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT meals_servings_check CHECK ((servings > 0))
);


--
-- Name: rehab_condition_mapping; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.rehab_condition_mapping (
    condition_id uuid NOT NULL,
    exercise_id uuid NOT NULL
);


--
-- Name: rehab_conditions; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.rehab_conditions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    slug text NOT NULL,
    name text NOT NULL,
    description text,
    image_url text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: rehab_exercises; Type: TABLE; Schema: library; Owner: -
--

CREATE TABLE library.rehab_exercises (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    slug text NOT NULL,
    title text NOT NULL,
    media_type text DEFAULT 'youtube'::text,
    youtube_id text,
    youtube_url text,
    thumbnail_url text,
    image_url text,
    description text,
    muscles_involved text[] DEFAULT '{}'::text[],
    categories text[] DEFAULT '{}'::text[],
    tags text[] DEFAULT '{}'::text[],
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: meal_plan_slot_meals; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.meal_plan_slot_meals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    meal_plan_id uuid NOT NULL,
    meal_id uuid NOT NULL,
    meal_type character varying NOT NULL,
    note text,
    CONSTRAINT meal_plan_slot_meals_meal_type_check CHECK (((meal_type)::text = ANY ((ARRAY['breakfast'::character varying, 'lunch'::character varying, 'dinner'::character varying, 'snack'::character varying])::text[])))
);


--
-- Name: meal_plans; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.meal_plans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title character varying NOT NULL,
    goal_type character varying,
    is_template boolean DEFAULT false NOT NULL,
    created_by uuid,
    creator_role character varying,
    start_date date,
    end_date date,
    description text,
    target_condition_id uuid,
    CONSTRAINT meal_plans_creator_role_check CHECK (((creator_role)::text = ANY ((ARRAY['admin'::character varying, 'user'::character varying])::text[]))),
    CONSTRAINT meal_plans_dates_check CHECK (((end_date IS NULL) OR (end_date >= start_date)))
);


--
-- Name: rehab_plans; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.rehab_plans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    condition_id uuid,
    title text NOT NULL,
    description text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: rehab_routine_exercises; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.rehab_routine_exercises (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    routine_id uuid,
    exercise_id uuid,
    sets integer,
    reps integer,
    hold_time_seconds integer,
    rest_seconds integer,
    notes text,
    order_index integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: rehab_routines; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.rehab_routines (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    plan_id uuid,
    name text NOT NULL,
    order_index integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: routine_exercises; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.routine_exercises (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workout_plan_routine_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    "position" integer DEFAULT 0 NOT NULL,
    sets integer,
    reps integer,
    weight_kg numeric,
    rest_time_seconds integer
);


--
-- Name: user_plan_enrollments; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.user_plan_enrollments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    workout_plan_id uuid,
    meal_plan_id uuid,
    status character varying DEFAULT 'active'::character varying NOT NULL,
    enrolled_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT user_plan_enrollments_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'paused'::character varying, 'completed'::character varying, 'dropped'::character varying])::text[])))
);


--
-- Name: workout_plan_routines; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.workout_plan_routines (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workout_plan_id uuid NOT NULL,
    name character varying NOT NULL,
    description text,
    day_number integer,
    day_of_week integer,
    is_rest_day boolean DEFAULT false NOT NULL,
    "position" integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: workout_plans; Type: TABLE; Schema: plans; Owner: -
--

CREATE TABLE plans.workout_plans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title character varying NOT NULL,
    difficulty_level character varying,
    is_template boolean DEFAULT false NOT NULL,
    created_by uuid,
    creator_role character varying,
    start_date date,
    end_date date,
    description text,
    schedule_type character varying DEFAULT 'nday'::character varying,
    duration_days integer DEFAULT 28 NOT NULL,
    CONSTRAINT workout_plans_creator_role_check CHECK (((creator_role)::text = ANY ((ARRAY['admin'::character varying, 'user'::character varying])::text[]))),
    CONSTRAINT workout_plans_dates_check CHECK (((end_date IS NULL) OR (end_date >= start_date))),
    CONSTRAINT workout_plans_difficulty_level_check CHECK (((difficulty_level)::text = ANY ((ARRAY['beginner'::character varying, 'intermediate'::character varying, 'advanced'::character varying])::text[]))),
    CONSTRAINT workout_plans_schedule_type_check CHECK (((schedule_type)::text = ANY ((ARRAY['nday'::character varying, 'weekly'::character varying])::text[])))
);


--
-- Name: health_profiles; Type: TABLE; Schema: profile; Owner: -
--

CREATE TABLE profile.health_profiles (
    user_id uuid NOT NULL,
    age integer,
    weight numeric(5,2),
    height numeric(5,2),
    primary_goal character varying,
    injury_details text,
    recovery_stage character varying,
    medical_diet_notes text,
    gender character varying(20),
    fitness_level character varying(20) DEFAULT 'Beginner'::character varying NOT NULL,
    activity_level character varying(30) DEFAULT 'Sedentary'::character varying NOT NULL,
    daily_calorie_target integer,
    current_streak integer DEFAULT 0 NOT NULL,
    longest_streak integer DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    bmi numeric(4,2) GENERATED ALWAYS AS (round((weight / ((height / (100)::numeric) * (height / (100)::numeric))), 2)) STORED,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_age CHECK (((age >= 5) AND (age <= 100))),
    CONSTRAINT chk_height CHECK (((height >= (50)::numeric) AND (height <= (280)::numeric))),
    CONSTRAINT chk_weight CHECK (((weight >= (20)::numeric) AND (weight <= (300)::numeric))),
    CONSTRAINT health_profiles_age_check CHECK (((age > 0) AND (age < 130)))
);


--
-- Name: user_chronic_conditions; Type: TABLE; Schema: profile; Owner: -
--

CREATE TABLE profile.user_chronic_conditions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    condition_name character varying NOT NULL,
    condition_id uuid
);


--
-- Name: COLUMN user_chronic_conditions.condition_id; Type: COMMENT; Schema: profile; Owner: -
--

COMMENT ON COLUMN profile.user_chronic_conditions.condition_id IS 'FK to library.conditions for pre-defined app conditions. condition_name is kept for free-text / unrecognized conditions.';


--
-- Name: users; Type: TABLE; Schema: profile; Owner: -
--

CREATE TABLE profile.users (
    id uuid NOT NULL,
    full_name character varying,
    role character varying DEFAULT 'general'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    username character varying,
    email character varying,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'rehab'::character varying, 'general'::character varying, 'fitness'::character varying])::text[])))
);


--
-- Name: health_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.health_profiles (
    profile_id uuid NOT NULL,
    user_id uuid NOT NULL,
    age smallint NOT NULL,
    weight numeric(5,2) NOT NULL,
    height numeric(5,2) NOT NULL,
    gender character varying(20),
    primary_goal character varying(30) NOT NULL,
    fitness_level character varying(20) NOT NULL,
    activity_level character varying(30) NOT NULL,
    daily_calorie_target integer,
    current_streak integer NOT NULL,
    longest_streak integer NOT NULL,
    injury_details character varying(500),
    recovery_stage character varying(100),
    medical_diet_notes character varying(1000),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    username character varying NOT NULL,
    email character varying NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: system; Owner: -
--

CREATE TABLE system.audit_logs (
    id bigint NOT NULL,
    actor_id uuid,
    actor_type character varying,
    action character varying NOT NULL,
    table_name character varying,
    old_values jsonb,
    new_values jsonb,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT audit_logs_actor_type_check CHECK (((actor_type)::text = ANY ((ARRAY['user'::character varying, 'admin'::character varying, 'system'::character varying])::text[])))
);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: system; Owner: -
--

CREATE SEQUENCE system.audit_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: system; Owner: -
--

ALTER SEQUENCE system.audit_logs_id_seq OWNED BY system.audit_logs.id;


--
-- Name: notifications; Type: TABLE; Schema: system; Owner: -
--

CREATE TABLE system.notifications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    title character varying NOT NULL,
    message text NOT NULL,
    type character varying NOT NULL,
    is_read boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT notifications_type_check CHECK (((type)::text = ANY ((ARRAY['info'::character varying, 'warning'::character varying, 'success'::character varying, 'alert'::character varying])::text[])))
);


--
-- Name: daily_logs; Type: TABLE; Schema: tracker; Owner: -
--

CREATE TABLE tracker.daily_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    date date NOT NULL,
    calories_consumed integer,
    workouts_completed integer,
    recovery_notes text,
    CONSTRAINT daily_logs_calories_consumed_check CHECK ((calories_consumed >= 0)),
    CONSTRAINT daily_logs_workouts_completed_check CHECK ((workouts_completed >= 0))
);


--
-- Name: user_meal_schedule; Type: TABLE; Schema: tracker; Owner: -
--

CREATE TABLE tracker.user_meal_schedule (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    meal_id uuid NOT NULL,
    scheduled_date timestamp without time zone NOT NULL,
    meal_type character varying NOT NULL,
    is_eaten boolean DEFAULT false NOT NULL,
    eaten_date timestamp without time zone,
    CONSTRAINT user_meal_schedule_meal_type_check CHECK (((meal_type)::text = ANY ((ARRAY['breakfast'::character varying, 'lunch'::character varying, 'dinner'::character varying, 'snack'::character varying])::text[])))
);


--
-- Name: workout_session_items; Type: TABLE; Schema: tracker; Owner: -
--

CREATE TABLE tracker.workout_session_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    set_number integer NOT NULL,
    reps_completed integer,
    weight_used numeric(6,2),
    is_completed boolean DEFAULT false NOT NULL,
    CONSTRAINT workout_session_items_reps_completed_check CHECK ((reps_completed >= 0)),
    CONSTRAINT workout_session_items_set_number_check CHECK ((set_number > 0)),
    CONSTRAINT workout_session_items_weight_used_check CHECK ((weight_used >= (0)::numeric))
);


--
-- Name: workout_sessions; Type: TABLE; Schema: tracker; Owner: -
--

CREATE TABLE tracker.workout_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    workout_plan_id uuid,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    status character varying DEFAULT 'scheduled'::character varying NOT NULL,
    scheduled_date date,
    routine_id uuid,
    CONSTRAINT workout_sessions_check CHECK (((completed_at IS NULL) OR (completed_at >= started_at))),
    CONSTRAINT workout_sessions_status_check CHECK (((status)::text = ANY ((ARRAY['scheduled'::character varying, 'in_progress'::character varying, 'completed'::character varying, 'abandoned'::character varying, 'skipped'::character varying])::text[])))
);


--
-- Name: Exercises ExerciseId; Type: DEFAULT; Schema: library; Owner: -
--

ALTER TABLE ONLY library."Exercises" ALTER COLUMN "ExerciseId" SET DEFAULT nextval('library."Exercises_ExerciseId_seq"'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: system; Owner: -
--

ALTER TABLE ONLY system.audit_logs ALTER COLUMN id SET DEFAULT nextval('system.audit_logs_id_seq'::regclass);


--
-- Name: Exercises Exercises_ExerciseCode_key; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library."Exercises"
    ADD CONSTRAINT "Exercises_ExerciseCode_key" UNIQUE ("ExerciseCode");


--
-- Name: Exercises Exercises_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library."Exercises"
    ADD CONSTRAINT "Exercises_pkey" PRIMARY KEY ("ExerciseId");


--
-- Name: condition_food_filters condition_food_filters_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.condition_food_filters
    ADD CONSTRAINT condition_food_filters_pkey PRIMARY KEY (id);


--
-- Name: condition_nutrition_rules condition_nutrition_rules_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.condition_nutrition_rules
    ADD CONSTRAINT condition_nutrition_rules_pkey PRIMARY KEY (id);


--
-- Name: conditions conditions_code_key; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.conditions
    ADD CONSTRAINT conditions_code_key UNIQUE (code);


--
-- Name: conditions conditions_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.conditions
    ADD CONSTRAINT conditions_pkey PRIMARY KEY (id);


--
-- Name: exercise_secondary_muscles exercise_secondary_muscles_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.exercise_secondary_muscles
    ADD CONSTRAINT exercise_secondary_muscles_pkey PRIMARY KEY (id);


--
-- Name: exercises exercises_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.exercises
    ADD CONSTRAINT exercises_pkey PRIMARY KEY (id);


--
-- Name: exercises exercises_source_id_key; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.exercises
    ADD CONSTRAINT exercises_source_id_key UNIQUE (source_id);


--
-- Name: ingredients ingredients_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.ingredients
    ADD CONSTRAINT ingredients_pkey PRIMARY KEY (id);


--
-- Name: meal_nutrition meal_nutrition_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.meal_nutrition
    ADD CONSTRAINT meal_nutrition_pkey PRIMARY KEY (meal_id);


--
-- Name: meal_tags meal_tags_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.meal_tags
    ADD CONSTRAINT meal_tags_pkey PRIMARY KEY (id);


--
-- Name: meals meals_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.meals
    ADD CONSTRAINT meals_pkey PRIMARY KEY (id);


--
-- Name: meals meals_title_unique; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.meals
    ADD CONSTRAINT meals_title_unique UNIQUE (title);


--
-- Name: rehab_condition_mapping rehab_condition_mapping_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.rehab_condition_mapping
    ADD CONSTRAINT rehab_condition_mapping_pkey PRIMARY KEY (condition_id, exercise_id);


--
-- Name: rehab_conditions rehab_conditions_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.rehab_conditions
    ADD CONSTRAINT rehab_conditions_pkey PRIMARY KEY (id);


--
-- Name: rehab_conditions rehab_conditions_slug_key; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.rehab_conditions
    ADD CONSTRAINT rehab_conditions_slug_key UNIQUE (slug);


--
-- Name: rehab_exercises rehab_exercises_pkey; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.rehab_exercises
    ADD CONSTRAINT rehab_exercises_pkey PRIMARY KEY (id);


--
-- Name: rehab_exercises rehab_exercises_slug_key; Type: CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.rehab_exercises
    ADD CONSTRAINT rehab_exercises_slug_key UNIQUE (slug);


--
-- Name: meal_plan_slot_meals meal_plan_slot_meals_meal_plan_id_meal_id_meal_type_key; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.meal_plan_slot_meals
    ADD CONSTRAINT meal_plan_slot_meals_meal_plan_id_meal_id_meal_type_key UNIQUE (meal_plan_id, meal_id, meal_type);


--
-- Name: meal_plan_slot_meals meal_plan_slot_meals_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.meal_plan_slot_meals
    ADD CONSTRAINT meal_plan_slot_meals_pkey PRIMARY KEY (id);


--
-- Name: meal_plans meal_plans_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.meal_plans
    ADD CONSTRAINT meal_plans_pkey PRIMARY KEY (id);


--
-- Name: rehab_plans rehab_plans_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.rehab_plans
    ADD CONSTRAINT rehab_plans_pkey PRIMARY KEY (id);


--
-- Name: rehab_routine_exercises rehab_routine_exercises_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.rehab_routine_exercises
    ADD CONSTRAINT rehab_routine_exercises_pkey PRIMARY KEY (id);


--
-- Name: rehab_routines rehab_routines_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.rehab_routines
    ADD CONSTRAINT rehab_routines_pkey PRIMARY KEY (id);


--
-- Name: routine_exercises routine_exercises_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.routine_exercises
    ADD CONSTRAINT routine_exercises_pkey PRIMARY KEY (id);


--
-- Name: user_plan_enrollments user_plan_enrollments_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.user_plan_enrollments
    ADD CONSTRAINT user_plan_enrollments_pkey PRIMARY KEY (id);


--
-- Name: workout_plan_routines workout_plan_routines_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.workout_plan_routines
    ADD CONSTRAINT workout_plan_routines_pkey PRIMARY KEY (id);


--
-- Name: workout_plans workout_plans_pkey; Type: CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.workout_plans
    ADD CONSTRAINT workout_plans_pkey PRIMARY KEY (id);


--
-- Name: health_profiles health_profiles_pkey; Type: CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.health_profiles
    ADD CONSTRAINT health_profiles_pkey PRIMARY KEY (user_id);


--
-- Name: user_chronic_conditions user_chronic_conditions_pkey; Type: CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.user_chronic_conditions
    ADD CONSTRAINT user_chronic_conditions_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: health_profiles health_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_profiles
    ADD CONSTRAINT health_profiles_pkey PRIMARY KEY (profile_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: system; Owner: -
--

ALTER TABLE ONLY system.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: system; Owner: -
--

ALTER TABLE ONLY system.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: daily_logs daily_logs_pkey; Type: CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.daily_logs
    ADD CONSTRAINT daily_logs_pkey PRIMARY KEY (id);


--
-- Name: daily_logs daily_logs_user_id_date_key; Type: CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.daily_logs
    ADD CONSTRAINT daily_logs_user_id_date_key UNIQUE (user_id, date);


--
-- Name: user_meal_schedule user_meal_schedule_pkey; Type: CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.user_meal_schedule
    ADD CONSTRAINT user_meal_schedule_pkey PRIMARY KEY (id);


--
-- Name: workout_session_items workout_session_items_pkey; Type: CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.workout_session_items
    ADD CONSTRAINT workout_session_items_pkey PRIMARY KEY (id);


--
-- Name: workout_sessions workout_sessions_pkey; Type: CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.workout_sessions
    ADD CONSTRAINT workout_sessions_pkey PRIMARY KEY (id);


--
-- Name: idx_condition_filters_condition; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_condition_filters_condition ON library.condition_food_filters USING btree (condition_id);


--
-- Name: idx_condition_rules_condition; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_condition_rules_condition ON library.condition_nutrition_rules USING btree (condition_id);


--
-- Name: idx_exercises_archived; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_exercises_archived ON library.exercises USING btree (is_archived);


--
-- Name: idx_exercises_muscle; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_exercises_muscle ON library.exercises USING btree (muscle_group);


--
-- Name: idx_exercises_type; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_exercises_type ON library.exercises USING btree (exercise_type);


--
-- Name: idx_ingredients_meal; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_ingredients_meal ON library.ingredients USING btree (meal_id);


--
-- Name: idx_meal_tags_meal; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_meal_tags_meal ON library.meal_tags USING btree (meal_id);


--
-- Name: idx_meals_title; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_meals_title ON library.meals USING btree (title);


--
-- Name: idx_sec_muscles_ex; Type: INDEX; Schema: library; Owner: -
--

CREATE INDEX idx_sec_muscles_ex ON library.exercise_secondary_muscles USING btree (exercise_id);


--
-- Name: idx_enrollments_status; Type: INDEX; Schema: plans; Owner: -
--

CREATE INDEX idx_enrollments_status ON plans.user_plan_enrollments USING btree (status);


--
-- Name: idx_enrollments_user; Type: INDEX; Schema: plans; Owner: -
--

CREATE INDEX idx_enrollments_user ON plans.user_plan_enrollments USING btree (user_id);


--
-- Name: idx_meal_plans_condition; Type: INDEX; Schema: plans; Owner: -
--

CREATE INDEX idx_meal_plans_condition ON plans.meal_plans USING btree (target_condition_id);


--
-- Name: idx_slot_meals_meal; Type: INDEX; Schema: plans; Owner: -
--

CREATE INDEX idx_slot_meals_meal ON plans.meal_plan_slot_meals USING btree (meal_id);


--
-- Name: idx_slot_meals_plan; Type: INDEX; Schema: plans; Owner: -
--

CREATE INDEX idx_slot_meals_plan ON plans.meal_plan_slot_meals USING btree (meal_plan_id);


--
-- Name: idx_slot_meals_type; Type: INDEX; Schema: plans; Owner: -
--

CREATE INDEX idx_slot_meals_type ON plans.meal_plan_slot_meals USING btree (meal_type);


--
-- Name: idx_chronic_conditions_user; Type: INDEX; Schema: profile; Owner: -
--

CREATE INDEX idx_chronic_conditions_user ON profile.user_chronic_conditions USING btree (user_id);


--
-- Name: idx_health_profiles_user; Type: INDEX; Schema: profile; Owner: -
--

CREATE INDEX idx_health_profiles_user ON profile.health_profiles USING btree (user_id);


--
-- Name: idx_profile_users_email; Type: INDEX; Schema: profile; Owner: -
--

CREATE INDEX idx_profile_users_email ON profile.users USING btree (email);


--
-- Name: idx_profile_users_role; Type: INDEX; Schema: profile; Owner: -
--

CREATE INDEX idx_profile_users_role ON profile.users USING btree (role);


--
-- Name: idx_profile_users_username; Type: INDEX; Schema: profile; Owner: -
--

CREATE INDEX idx_profile_users_username ON profile.users USING btree (username);


--
-- Name: idx_user_chronic_condition_id; Type: INDEX; Schema: profile; Owner: -
--

CREATE INDEX idx_user_chronic_condition_id ON profile.user_chronic_conditions USING btree (condition_id);


--
-- Name: ix_public_health_profiles_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_public_health_profiles_user_id ON public.health_profiles USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: idx_audit_actor; Type: INDEX; Schema: system; Owner: -
--

CREATE INDEX idx_audit_actor ON system.audit_logs USING btree (actor_id);


--
-- Name: idx_audit_table; Type: INDEX; Schema: system; Owner: -
--

CREATE INDEX idx_audit_table ON system.audit_logs USING btree (table_name);


--
-- Name: idx_audit_timestamp; Type: INDEX; Schema: system; Owner: -
--

CREATE INDEX idx_audit_timestamp ON system.audit_logs USING btree ("timestamp");


--
-- Name: idx_notifications_read; Type: INDEX; Schema: system; Owner: -
--

CREATE INDEX idx_notifications_read ON system.notifications USING btree (is_read);


--
-- Name: idx_notifications_user; Type: INDEX; Schema: system; Owner: -
--

CREATE INDEX idx_notifications_user ON system.notifications USING btree (user_id);


--
-- Name: idx_daily_logs_date; Type: INDEX; Schema: tracker; Owner: -
--

CREATE INDEX idx_daily_logs_date ON tracker.daily_logs USING btree (date);


--
-- Name: idx_daily_logs_user; Type: INDEX; Schema: tracker; Owner: -
--

CREATE INDEX idx_daily_logs_user ON tracker.daily_logs USING btree (user_id);


--
-- Name: idx_meal_sched_date; Type: INDEX; Schema: tracker; Owner: -
--

CREATE INDEX idx_meal_sched_date ON tracker.user_meal_schedule USING btree (scheduled_date);


--
-- Name: idx_meal_sched_user; Type: INDEX; Schema: tracker; Owner: -
--

CREATE INDEX idx_meal_sched_user ON tracker.user_meal_schedule USING btree (user_id);


--
-- Name: idx_session_items_session; Type: INDEX; Schema: tracker; Owner: -
--

CREATE INDEX idx_session_items_session ON tracker.workout_session_items USING btree (session_id);


--
-- Name: idx_sessions_plan; Type: INDEX; Schema: tracker; Owner: -
--

CREATE INDEX idx_sessions_plan ON tracker.workout_sessions USING btree (workout_plan_id);


--
-- Name: idx_sessions_status; Type: INDEX; Schema: tracker; Owner: -
--

CREATE INDEX idx_sessions_status ON tracker.workout_sessions USING btree (status);


--
-- Name: idx_sessions_user; Type: INDEX; Schema: tracker; Owner: -
--

CREATE INDEX idx_sessions_user ON tracker.workout_sessions USING btree (user_id);


--
-- Name: condition_food_filters condition_food_filters_condition_id_fkey; Type: FK CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.condition_food_filters
    ADD CONSTRAINT condition_food_filters_condition_id_fkey FOREIGN KEY (condition_id) REFERENCES library.conditions(id) ON DELETE CASCADE;


--
-- Name: condition_nutrition_rules condition_nutrition_rules_condition_id_fkey; Type: FK CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.condition_nutrition_rules
    ADD CONSTRAINT condition_nutrition_rules_condition_id_fkey FOREIGN KEY (condition_id) REFERENCES library.conditions(id) ON DELETE CASCADE;


--
-- Name: exercise_secondary_muscles exercise_secondary_muscles_exercise_id_fkey; Type: FK CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.exercise_secondary_muscles
    ADD CONSTRAINT exercise_secondary_muscles_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES library.exercises(id) ON DELETE CASCADE;


--
-- Name: ingredients ingredients_meal_id_fkey; Type: FK CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.ingredients
    ADD CONSTRAINT ingredients_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES library.meals(id) ON DELETE CASCADE;


--
-- Name: meal_nutrition meal_nutrition_meal_id_fkey; Type: FK CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.meal_nutrition
    ADD CONSTRAINT meal_nutrition_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES library.meals(id) ON DELETE CASCADE;


--
-- Name: meal_tags meal_tags_meal_id_fkey; Type: FK CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.meal_tags
    ADD CONSTRAINT meal_tags_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES library.meals(id) ON DELETE CASCADE;


--
-- Name: rehab_condition_mapping rehab_condition_mapping_condition_id_fkey; Type: FK CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.rehab_condition_mapping
    ADD CONSTRAINT rehab_condition_mapping_condition_id_fkey FOREIGN KEY (condition_id) REFERENCES library.rehab_conditions(id) ON DELETE CASCADE;


--
-- Name: rehab_condition_mapping rehab_condition_mapping_exercise_id_fkey; Type: FK CONSTRAINT; Schema: library; Owner: -
--

ALTER TABLE ONLY library.rehab_condition_mapping
    ADD CONSTRAINT rehab_condition_mapping_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES library.rehab_exercises(id) ON DELETE CASCADE;


--
-- Name: meal_plan_slot_meals meal_plan_slot_meals_meal_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.meal_plan_slot_meals
    ADD CONSTRAINT meal_plan_slot_meals_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES library.meals(id) ON DELETE RESTRICT;


--
-- Name: meal_plan_slot_meals meal_plan_slot_meals_meal_plan_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.meal_plan_slot_meals
    ADD CONSTRAINT meal_plan_slot_meals_meal_plan_id_fkey FOREIGN KEY (meal_plan_id) REFERENCES plans.meal_plans(id) ON DELETE CASCADE;


--
-- Name: meal_plans meal_plans_created_by_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.meal_plans
    ADD CONSTRAINT meal_plans_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL;


--
-- Name: meal_plans meal_plans_target_condition_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.meal_plans
    ADD CONSTRAINT meal_plans_target_condition_id_fkey FOREIGN KEY (target_condition_id) REFERENCES library.conditions(id) ON DELETE SET NULL;


--
-- Name: rehab_plans rehab_plans_condition_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.rehab_plans
    ADD CONSTRAINT rehab_plans_condition_id_fkey FOREIGN KEY (condition_id) REFERENCES library.rehab_conditions(id) ON DELETE SET NULL;


--
-- Name: rehab_plans rehab_plans_user_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.rehab_plans
    ADD CONSTRAINT rehab_plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: rehab_routine_exercises rehab_routine_exercises_exercise_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.rehab_routine_exercises
    ADD CONSTRAINT rehab_routine_exercises_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES library.rehab_exercises(id) ON DELETE RESTRICT;


--
-- Name: rehab_routine_exercises rehab_routine_exercises_routine_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.rehab_routine_exercises
    ADD CONSTRAINT rehab_routine_exercises_routine_id_fkey FOREIGN KEY (routine_id) REFERENCES plans.rehab_routines(id) ON DELETE CASCADE;


--
-- Name: rehab_routines rehab_routines_plan_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.rehab_routines
    ADD CONSTRAINT rehab_routines_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans.rehab_plans(id) ON DELETE CASCADE;


--
-- Name: routine_exercises routine_exercises_exercise_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.routine_exercises
    ADD CONSTRAINT routine_exercises_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES library.exercises(id);


--
-- Name: routine_exercises routine_exercises_workout_plan_routine_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.routine_exercises
    ADD CONSTRAINT routine_exercises_workout_plan_routine_id_fkey FOREIGN KEY (workout_plan_routine_id) REFERENCES plans.workout_plan_routines(id) ON DELETE CASCADE;


--
-- Name: user_plan_enrollments user_plan_enrollments_meal_plan_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.user_plan_enrollments
    ADD CONSTRAINT user_plan_enrollments_meal_plan_id_fkey FOREIGN KEY (meal_plan_id) REFERENCES plans.meal_plans(id) ON DELETE SET NULL;


--
-- Name: user_plan_enrollments user_plan_enrollments_user_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.user_plan_enrollments
    ADD CONSTRAINT user_plan_enrollments_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: user_plan_enrollments user_plan_enrollments_workout_plan_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.user_plan_enrollments
    ADD CONSTRAINT user_plan_enrollments_workout_plan_id_fkey FOREIGN KEY (workout_plan_id) REFERENCES plans.workout_plans(id) ON DELETE SET NULL;


--
-- Name: workout_plan_routines workout_plan_routines_workout_plan_id_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.workout_plan_routines
    ADD CONSTRAINT workout_plan_routines_workout_plan_id_fkey FOREIGN KEY (workout_plan_id) REFERENCES plans.workout_plans(id) ON DELETE CASCADE;


--
-- Name: workout_plans workout_plans_created_by_fkey; Type: FK CONSTRAINT; Schema: plans; Owner: -
--

ALTER TABLE ONLY plans.workout_plans
    ADD CONSTRAINT workout_plans_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE SET NULL;


--
-- Name: health_profiles health_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.health_profiles
    ADD CONSTRAINT health_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: user_chronic_conditions user_chronic_conditions_condition_id_fkey; Type: FK CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.user_chronic_conditions
    ADD CONSTRAINT user_chronic_conditions_condition_id_fkey FOREIGN KEY (condition_id) REFERENCES library.conditions(id) ON DELETE SET NULL;


--
-- Name: user_chronic_conditions user_chronic_conditions_user_id_fkey; Type: FK CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.user_chronic_conditions
    ADD CONSTRAINT user_chronic_conditions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: users users_id_fkey; Type: FK CONSTRAINT; Schema: profile; Owner: -
--

ALTER TABLE ONLY profile.users
    ADD CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: system; Owner: -
--

ALTER TABLE ONLY system.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: daily_logs daily_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.daily_logs
    ADD CONSTRAINT daily_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: user_meal_schedule user_meal_schedule_meal_id_fkey; Type: FK CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.user_meal_schedule
    ADD CONSTRAINT user_meal_schedule_meal_id_fkey FOREIGN KEY (meal_id) REFERENCES library.meals(id) ON DELETE RESTRICT;


--
-- Name: user_meal_schedule user_meal_schedule_user_id_fkey; Type: FK CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.user_meal_schedule
    ADD CONSTRAINT user_meal_schedule_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: workout_session_items workout_session_items_exercise_id_fkey; Type: FK CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.workout_session_items
    ADD CONSTRAINT workout_session_items_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES library.exercises(id) ON DELETE RESTRICT;


--
-- Name: workout_session_items workout_session_items_session_id_fkey; Type: FK CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.workout_session_items
    ADD CONSTRAINT workout_session_items_session_id_fkey FOREIGN KEY (session_id) REFERENCES tracker.workout_sessions(id) ON DELETE CASCADE;


--
-- Name: workout_sessions workout_sessions_routine_id_fkey; Type: FK CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.workout_sessions
    ADD CONSTRAINT workout_sessions_routine_id_fkey FOREIGN KEY (routine_id) REFERENCES plans.workout_plan_routines(id);


--
-- Name: workout_sessions workout_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.workout_sessions
    ADD CONSTRAINT workout_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: workout_sessions workout_sessions_workout_plan_id_fkey; Type: FK CONSTRAINT; Schema: tracker; Owner: -
--

ALTER TABLE ONLY tracker.workout_sessions
    ADD CONSTRAINT workout_sessions_workout_plan_id_fkey FOREIGN KEY (workout_plan_id) REFERENCES plans.workout_plans(id) ON DELETE SET NULL;


--
-- Name: condition_food_filters admins: manage condition filters; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "admins: manage condition filters" ON library.condition_food_filters USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: condition_nutrition_rules admins: manage condition rules; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "admins: manage condition rules" ON library.condition_nutrition_rules USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: conditions admins: manage conditions; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "admins: manage conditions" ON library.conditions USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: exercises admins: manage exercises; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "admins: manage exercises" ON library.exercises USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: meals admins: manage meals; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "admins: manage meals" ON library.meals USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: condition_food_filters; Type: ROW SECURITY; Schema: library; Owner: -
--

ALTER TABLE library.condition_food_filters ENABLE ROW LEVEL SECURITY;

--
-- Name: condition_nutrition_rules; Type: ROW SECURITY; Schema: library; Owner: -
--

ALTER TABLE library.condition_nutrition_rules ENABLE ROW LEVEL SECURITY;

--
-- Name: conditions; Type: ROW SECURITY; Schema: library; Owner: -
--

ALTER TABLE library.conditions ENABLE ROW LEVEL SECURITY;

--
-- Name: condition_food_filters everyone: read condition filters; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "everyone: read condition filters" ON library.condition_food_filters FOR SELECT USING (true);


--
-- Name: condition_nutrition_rules everyone: read condition rules; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "everyone: read condition rules" ON library.condition_nutrition_rules FOR SELECT USING (true);


--
-- Name: conditions everyone: read conditions; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "everyone: read conditions" ON library.conditions FOR SELECT USING (true);


--
-- Name: exercises everyone: read exercises; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "everyone: read exercises" ON library.exercises FOR SELECT USING (true);


--
-- Name: meals everyone: read meals; Type: POLICY; Schema: library; Owner: -
--

CREATE POLICY "everyone: read meals" ON library.meals FOR SELECT USING (true);


--
-- Name: exercises; Type: ROW SECURITY; Schema: library; Owner: -
--

ALTER TABLE library.exercises ENABLE ROW LEVEL SECURITY;

--
-- Name: meals; Type: ROW SECURITY; Schema: library; Owner: -
--

ALTER TABLE library.meals ENABLE ROW LEVEL SECURITY;

--
-- Name: rehab_condition_mapping; Type: ROW SECURITY; Schema: library; Owner: -
--

ALTER TABLE library.rehab_condition_mapping ENABLE ROW LEVEL SECURITY;

--
-- Name: rehab_conditions; Type: ROW SECURITY; Schema: library; Owner: -
--

ALTER TABLE library.rehab_conditions ENABLE ROW LEVEL SECURITY;

--
-- Name: rehab_exercises; Type: ROW SECURITY; Schema: library; Owner: -
--

ALTER TABLE library.rehab_exercises ENABLE ROW LEVEL SECURITY;

--
-- Name: meal_plans admins: full access meal plans; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "admins: full access meal plans" ON plans.meal_plans USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: meal_plan_slot_meals admins: full access slot meals; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "admins: full access slot meals" ON plans.meal_plan_slot_meals USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: workout_plans admins: full access workout plans; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "admins: full access workout plans" ON plans.workout_plans USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: meal_plan_slot_meals; Type: ROW SECURITY; Schema: plans; Owner: -
--

ALTER TABLE plans.meal_plan_slot_meals ENABLE ROW LEVEL SECURITY;

--
-- Name: meal_plans; Type: ROW SECURITY; Schema: plans; Owner: -
--

ALTER TABLE plans.meal_plans ENABLE ROW LEVEL SECURITY;

--
-- Name: rehab_plans; Type: ROW SECURITY; Schema: plans; Owner: -
--

ALTER TABLE plans.rehab_plans ENABLE ROW LEVEL SECURITY;

--
-- Name: rehab_routine_exercises; Type: ROW SECURITY; Schema: plans; Owner: -
--

ALTER TABLE plans.rehab_routine_exercises ENABLE ROW LEVEL SECURITY;

--
-- Name: rehab_routines; Type: ROW SECURITY; Schema: plans; Owner: -
--

ALTER TABLE plans.rehab_routines ENABLE ROW LEVEL SECURITY;

--
-- Name: routine_exercises; Type: ROW SECURITY; Schema: plans; Owner: -
--

ALTER TABLE plans.routine_exercises ENABLE ROW LEVEL SECURITY;

--
-- Name: meal_plans users: manage own meal plans; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "users: manage own meal plans" ON plans.meal_plans USING (((is_template = false) AND (created_by = auth.uid())));


--
-- Name: workout_plans users: manage own plans; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "users: manage own plans" ON plans.workout_plans USING (((is_template = false) AND (created_by = auth.uid())));


--
-- Name: meal_plan_slot_meals users: manage slot meals for own plans; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "users: manage slot meals for own plans" ON plans.meal_plan_slot_meals USING ((EXISTS ( SELECT 1
   FROM plans.meal_plans mp
  WHERE ((mp.id = meal_plan_slot_meals.meal_plan_id) AND (mp.is_template = false) AND (mp.created_by = auth.uid())))));


--
-- Name: meal_plans users: read meal templates; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "users: read meal templates" ON plans.meal_plans FOR SELECT USING ((is_template = true));


--
-- Name: meal_plan_slot_meals users: read slot meals for own or template plans; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "users: read slot meals for own or template plans" ON plans.meal_plan_slot_meals FOR SELECT USING ((EXISTS ( SELECT 1
   FROM plans.meal_plans mp
  WHERE ((mp.id = meal_plan_slot_meals.meal_plan_id) AND ((mp.is_template = true) OR (mp.created_by = auth.uid()))))));


--
-- Name: workout_plans users: read templates; Type: POLICY; Schema: plans; Owner: -
--

CREATE POLICY "users: read templates" ON plans.workout_plans FOR SELECT USING ((is_template = true));


--
-- Name: workout_plan_routines; Type: ROW SECURITY; Schema: plans; Owner: -
--

ALTER TABLE plans.workout_plan_routines ENABLE ROW LEVEL SECURITY;

--
-- Name: workout_plans; Type: ROW SECURITY; Schema: plans; Owner: -
--

ALTER TABLE plans.workout_plans ENABLE ROW LEVEL SECURITY;

--
-- Name: users admins: read all profiles; Type: POLICY; Schema: profile; Owner: -
--

CREATE POLICY "admins: read all profiles" ON profile.users FOR SELECT USING (((( SELECT users_1.role
   FROM profile.users users_1
  WHERE (users_1.id = auth.uid())))::text = 'admin'::text));


--
-- Name: users; Type: ROW SECURITY; Schema: profile; Owner: -
--

ALTER TABLE profile.users ENABLE ROW LEVEL SECURITY;

--
-- Name: users users: read own profile; Type: POLICY; Schema: profile; Owner: -
--

CREATE POLICY "users: read own profile" ON profile.users FOR SELECT USING ((auth.uid() = id));


--
-- Name: users users: update own profile; Type: POLICY; Schema: profile; Owner: -
--

CREATE POLICY "users: update own profile" ON profile.users FOR UPDATE USING ((auth.uid() = id));


--
-- Name: notifications admins: manage notifications; Type: POLICY; Schema: system; Owner: -
--

CREATE POLICY "admins: manage notifications" ON system.notifications USING (((( SELECT users.role
   FROM profile.users
  WHERE (users.id = auth.uid())))::text = 'admin'::text));


--
-- Name: notifications; Type: ROW SECURITY; Schema: system; Owner: -
--

ALTER TABLE system.notifications ENABLE ROW LEVEL SECURITY;

--
-- Name: notifications users: own notifications; Type: POLICY; Schema: system; Owner: -
--

CREATE POLICY "users: own notifications" ON system.notifications FOR SELECT USING ((user_id = auth.uid()));


--
-- Name: daily_logs; Type: ROW SECURITY; Schema: tracker; Owner: -
--

ALTER TABLE tracker.daily_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: user_meal_schedule; Type: ROW SECURITY; Schema: tracker; Owner: -
--

ALTER TABLE tracker.user_meal_schedule ENABLE ROW LEVEL SECURITY;

--
-- Name: daily_logs users: own daily logs; Type: POLICY; Schema: tracker; Owner: -
--

CREATE POLICY "users: own daily logs" ON tracker.daily_logs USING ((user_id = auth.uid()));


--
-- Name: user_meal_schedule users: own meal schedule; Type: POLICY; Schema: tracker; Owner: -
--

CREATE POLICY "users: own meal schedule" ON tracker.user_meal_schedule USING ((user_id = auth.uid()));


--
-- Name: workout_sessions users: own sessions; Type: POLICY; Schema: tracker; Owner: -
--

CREATE POLICY "users: own sessions" ON tracker.workout_sessions USING ((user_id = auth.uid()));


--
-- Name: workout_sessions; Type: ROW SECURITY; Schema: tracker; Owner: -
--

ALTER TABLE tracker.workout_sessions ENABLE ROW LEVEL SECURITY;

--
-- Name: supabase_realtime; Type: PUBLICATION; Schema: -; Owner: -
--

CREATE PUBLICATION supabase_realtime WITH (publish = 'insert, update, delete, truncate');


--
-- Name: supabase_realtime users; Type: PUBLICATION TABLE; Schema: auth; Owner: -
--

ALTER PUBLICATION supabase_realtime ADD TABLE ONLY auth.users;


--
-- Name: supabase_realtime exercises; Type: PUBLICATION TABLE; Schema: library; Owner: -
--

ALTER PUBLICATION supabase_realtime ADD TABLE ONLY library.exercises;


--
-- Name: issue_graphql_placeholder; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_graphql_placeholder ON sql_drop
         WHEN TAG IN ('DROP EXTENSION')
   EXECUTE FUNCTION extensions.set_graphql_placeholder();


--
-- Name: issue_pg_cron_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_cron_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_cron_access();


--
-- Name: issue_pg_graphql_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_graphql_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_graphql_access();


--
-- Name: issue_pg_net_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_net_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_net_access();


--
-- Name: pgrst_ddl_watch; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER pgrst_ddl_watch ON ddl_command_end
   EXECUTE FUNCTION extensions.pgrst_ddl_watch();


--
-- Name: pgrst_drop_watch; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER pgrst_drop_watch ON sql_drop
   EXECUTE FUNCTION extensions.pgrst_drop_watch();


--
-- PostgreSQL database dump complete
--

\unrestrict rbHPrFuMmrucJid4cS0vewt4cW99e1afpQbqEjajEPjNgBr3emGeZHLmEmq1lU8

