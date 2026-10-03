

ALTER TYPE "public"."app_role" OWNER TO "postgres";


CREATE TYPE "public"."notification_type" AS ENUM (
    'like',
    'comment'
);


ALTER TYPE "public"."notification_type" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."check_username_exists"("username_to_check" "text") RETURNS boolean
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  SELECT EXISTS (
    SELECT 1 
    FROM public.profiles 
    WHERE username = username_to_check
  );
$$;


ALTER FUNCTION "public"."check_username_exists"("username_to_check" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_comment_notification"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  milk_test_data RECORD;
  preferences RECORD;
  product_desc TEXT;
BEGIN
  -- Get the milk test owner and detailed product data
  SELECT 
    mt.user_id, 
