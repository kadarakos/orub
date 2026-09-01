module Util exposing (nonEmpty, nonEmptyOr)


nonEmpty : String -> Maybe String
nonEmpty raw =
    case String.trim raw of
        "" ->
            Nothing

        trimmed ->
            Just trimmed


nonEmptyOr : String -> String -> String
nonEmptyOr default raw =
    Maybe.withDefault default (nonEmpty raw)
