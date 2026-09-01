module Page.Search exposing
    ( Candidate
    , Model
    , Msg(..)
    , Release
    , SearchResult(..)
    , init
    , searchResultDecoder
    , update
    , view
    )

import Api
import Dict exposing (Dict)
import Html exposing (Html, a, button, div, form, input, label, span, table, tbody, td, text, th, thead, tr)
import Html.Attributes exposing (class, href, placeholder, rel, target, type_, value)
import Html.Events exposing (onClick, onInput, onSubmit)
import Http
import Json.Decode as Decode exposing (Decoder)
import Json.Encode as Encode
import Util



-- MODEL


type alias Model =
    { releaseTitle : String
    , trackTitle : String
    , artist : String
    , label : String
    , year : String
    , status : Status
    , candidateStates : Dict Int RowState
    }


type Status
    = Idle
    | Loading
    | Loaded SearchResult
    | Failed String


type RowState
    = NotAdded
    | Adding
    | AddedCreated Release (List Int)
    | AddedAlready Release (List Int)
    | AddFailed String


type SearchResult
    = Created Release (List Int)
    | AlreadyExists Release (List Int)
    | Ambiguous (List Candidate)
    | NotFound


type alias Release =
    { id : Int
    , title : String
    , year : Maybe Int
    , format : String
    }


type alias Candidate =
    { id : Int
    , title : String
    , year : Maybe Int
    , label : List String
    , format : List String
    }


init : ( Model, Cmd Msg )
init =
    ( { releaseTitle = ""
      , trackTitle = ""
      , artist = ""
      , label = ""
      , year = ""
      , status = Idle
      , candidateStates = Dict.empty
      }
    , Cmd.none
    )



-- DECODERS / ENCODERS


searchResultDecoder : Decoder SearchResult
searchResultDecoder =
    Decode.field "status" Decode.string
        |> Decode.andThen searchResultFromStatus


searchResultFromStatus : String -> Decoder SearchResult
searchResultFromStatus status =
    case status of
        "created" ->
            Decode.map2 Created (Decode.field "release" releaseDecoder) suggestedTagIdsDecoder

        "already_exists" ->
            Decode.map2 AlreadyExists (Decode.field "release" releaseDecoder) suggestedTagIdsDecoder

        "ambiguous" ->
            Decode.map Ambiguous (Decode.field "candidates" (Decode.list candidateDecoder))

        "not_found" ->
            Decode.succeed NotFound

        other ->
            Decode.fail ("unknown search status: " ++ other)


suggestedTagIdsDecoder : Decoder (List Int)
suggestedTagIdsDecoder =
    Decode.field "suggested_tag_ids" (Decode.nullable (Decode.list Decode.int))
        |> Decode.map (Maybe.withDefault [])


releaseDecoder : Decoder Release
releaseDecoder =
    Decode.map4 Release
        (Decode.field "id" Decode.int)
        (Decode.field "title" Decode.string)
        (Decode.field "year" (Decode.nullable Decode.int))
        (Decode.field "format" Decode.string)


candidateDecoder : Decoder Candidate
candidateDecoder =
    Decode.map5 Candidate
        (Decode.field "id" Decode.int)
        (Decode.field "title" Decode.string)
        (Decode.field "year" (Decode.nullable Decode.int))
        (Decode.field "label" (Decode.list Decode.string))
        (Decode.field "format" (Decode.list Decode.string))


encodeRequest : Model -> Encode.Value
encodeRequest model =
    Encode.object
        (List.filterMap identity
            [ encodeField "release_title" Encode.string (Util.nonEmpty model.releaseTitle)
            , encodeField "track_title" Encode.string (Util.nonEmpty model.trackTitle)
            , encodeField "artist" Encode.string (Util.nonEmpty model.artist)
            , encodeField "label" Encode.string (Util.nonEmpty model.label)
            , encodeField "year" Encode.int (String.toInt (String.trim model.year))
            ]
        )


encodeField : String -> (a -> Encode.Value) -> Maybe a -> Maybe ( String, Encode.Value )
encodeField key toValue maybeValue =
    Maybe.map (\v -> ( key, toValue v )) maybeValue



-- UPDATE


type Msg
    = ReleaseTitleChanged String
    | TrackTitleChanged String
    | ArtistChanged String
    | LabelChanged String
    | YearChanged String
    | Submit
    | GotResponse (Result Http.Error SearchResult)
    | AddCandidate Int
    | GotIngestResponse Int (Result Http.Error SearchResult)
    | OpenAddDetails Int (List Int)


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        ReleaseTitleChanged v ->
            ( { model | releaseTitle = v }, Cmd.none )

        TrackTitleChanged v ->
            ( { model | trackTitle = v }, Cmd.none )

        ArtistChanged v ->
            ( { model | artist = v }, Cmd.none )

        LabelChanged v ->
            ( { model | label = v }, Cmd.none )

        YearChanged v ->
            ( { model | year = v }, Cmd.none )

        Submit ->
            ( { model | status = Loading, candidateStates = Dict.empty }, postSearch model )

        GotResponse (Ok result) ->
            ( { model | status = Loaded result }, Cmd.none )

        GotResponse (Err error) ->
            ( { model | status = Failed (Api.httpErrorToString error) }, Cmd.none )

        AddCandidate candidateId ->
            ( { model | candidateStates = Dict.insert candidateId Adding model.candidateStates }
            , postIngest candidateId
            )

        GotIngestResponse candidateId (Ok result) ->
            ( { model | candidateStates = Dict.insert candidateId (rowStateFromResult result) model.candidateStates }
            , Cmd.none
            )

        GotIngestResponse candidateId (Err error) ->
            ( { model
                | candidateStates =
                    Dict.insert candidateId (AddFailed (Api.httpErrorToString error)) model.candidateStates
              }
            , Cmd.none
            )

        OpenAddDetails _ _ ->
            -- Intercepted by Main before it reaches here; kept for exhaustiveness.
            ( model, Cmd.none )


rowStateFromResult : SearchResult -> RowState
rowStateFromResult result =
    case result of
        Created release suggested ->
            AddedCreated release suggested

        AlreadyExists release suggested ->
            AddedAlready release suggested

        Ambiguous _ ->
            AddFailed "unexpected response: ingest returned ambiguous"

        NotFound ->
            AddFailed "unexpected response: ingest returned not_found"


postSearch : Model -> Cmd Msg
postSearch model =
    Http.post
        { url = Api.apiBaseUrl ++ "/releases/search"
        , body = Http.jsonBody (encodeRequest model)
        , expect = Http.expectJson GotResponse searchResultDecoder
        }


postIngest : Int -> Cmd Msg
postIngest candidateId =
    Http.post
        { url = Api.apiBaseUrl ++ "/releases/" ++ String.fromInt candidateId ++ "/ingest"
        , body = Http.emptyBody
        , expect = Http.expectJson (GotIngestResponse candidateId) searchResultDecoder
        }


discogsUrl : Int -> String
discogsUrl candidateId =
    "https://www.discogs.com/release/" ++ String.fromInt candidateId



-- VIEW


view : Model -> Html Msg
view model =
    div []
        [ viewForm model
        , viewStatus model.status model.candidateStates
        ]


viewForm : Model -> Html Msg
viewForm model =
    form [ class "panel search-form", onSubmit Submit ]
        [ viewField "release title" model.releaseTitle ReleaseTitleChanged "text"
        , viewField "track title" model.trackTitle TrackTitleChanged "text"
        , viewField "artist" model.artist ArtistChanged "text"
        , viewField "label" model.label LabelChanged "text"
        , viewField "year" model.year YearChanged "number"
        , button [ class "submit-btn", type_ "submit" ] [ text "search" ]
        ]


viewField : String -> String -> (String -> Msg) -> String -> Html Msg
viewField labelText fieldValue toMsg inputType =
    div [ class "field" ]
        [ label [ class "field-label" ] [ text labelText ]
        , input
            [ class "field-input"
            , type_ inputType
            , value fieldValue
            , placeholder labelText
            , onInput toMsg
            ]
            []
        ]


viewStatus : Status -> Dict Int RowState -> Html Msg
viewStatus status candidateStates =
    case status of
        Idle ->
            text ""

        Loading ->
            div [ class "panel status-line loading" ] [ text "searching_" ]

        Failed message ->
            div [ class "panel status-line error" ] [ text message ]

        Loaded result ->
            viewResponse result candidateStates


viewResponse : SearchResult -> Dict Int RowState -> Html Msg
viewResponse result candidateStates =
    case result of
        Created release suggested ->
            div [ class "panel status-line ok" ]
                [ span [ class "tag" ] [ text "created" ]
                , viewRelease release
                , button
                    [ class "add-btn"
                    , type_ "button"
                    , onClick (OpenAddDetails release.id suggested)
                    ]
                    [ text "add details →" ]
                ]

        AlreadyExists release suggested ->
            div [ class "panel status-line ok" ]
                [ span [ class "tag" ] [ text "already exists" ]
                , viewRelease release
                , button
                    [ class "add-btn"
                    , type_ "button"
                    , onClick (OpenAddDetails release.id suggested)
                    ]
                    [ text "add details →" ]
                ]

        NotFound ->
            div [ class "panel status-line" ] [ text "no match found" ]

        Ambiguous candidates ->
            div [ class "panel candidates" ]
                [ div [ class "status-line" ]
                    [ span [ class "tag warn" ] [ text "ambiguous" ]
                    , text (String.fromInt (List.length candidates) ++ " candidates")
                    ]
                , viewCandidateTable candidates candidateStates
                ]


viewRelease : Release -> Html Msg
viewRelease release =
    div [ class "release" ]
        [ span [ class "release-title" ] [ text release.title ]
        , span [ class "release-meta" ]
            [ text (Maybe.withDefault "?" (Maybe.map String.fromInt release.year) ++ " · " ++ release.format ++ " · id=" ++ String.fromInt release.id) ]
        ]


viewCandidateTable : List Candidate -> Dict Int RowState -> Html Msg
viewCandidateTable candidates candidateStates =
    table [ class "candidate-table" ]
        [ thead []
            [ tr []
                [ th [] [ text "id" ]
                , th [] [ text "title" ]
                , th [] [ text "year" ]
                , th [] [ text "label" ]
                , th [] [ text "format" ]
                , th [] [ text "add" ]
                , th [] [ text "discogs" ]
                ]
            ]
        , tbody []
            (List.map
                (\candidate ->
                    viewCandidateRow candidate
                        (Dict.get candidate.id candidateStates |> Maybe.withDefault NotAdded)
                )
                candidates
            )
        ]


viewCandidateRow : Candidate -> RowState -> Html Msg
viewCandidateRow candidate rowState =
    tr []
        [ td [] [ text (String.fromInt candidate.id) ]
        , td [] [ text candidate.title ]
        , td [] [ text (Maybe.withDefault "—" (Maybe.map String.fromInt candidate.year)) ]
        , td [] [ text (String.join ", " (List.take 2 candidate.label)) ]
        , td [] [ text (String.join ", " (List.take 2 candidate.format)) ]
        , td [] [ viewAddCell candidate.id rowState ]
        , td []
            [ a
                [ href (discogsUrl candidate.id)
                , target "_blank"
                , rel "noopener noreferrer"
                , class "discogs-link"
                ]
                [ text "↗" ]
            ]
        ]


viewAddCell : Int -> RowState -> Html Msg
viewAddCell candidateId rowState =
    case rowState of
        NotAdded ->
            button [ class "add-btn", type_ "button", onClick (AddCandidate candidateId) ] [ text "add" ]

        Adding ->
            span [ class "dim" ] [ text "adding_" ]

        AddedCreated release suggested ->
            div [ class "added-cell" ]
                [ span [ class "tag" ] [ text "created" ]
                , button
                    [ class "add-btn"
                    , type_ "button"
                    , onClick (OpenAddDetails release.id suggested)
                    ]
                    [ text "details" ]
                ]

        AddedAlready release suggested ->
            div [ class "added-cell" ]
                [ span [ class "tag" ] [ text "exists" ]
                , button
                    [ class "add-btn"
                    , type_ "button"
                    , onClick (OpenAddDetails release.id suggested)
                    ]
                    [ text "details" ]
                ]

        AddFailed message ->
            button
                [ class "add-btn error"
                , type_ "button"
                , Html.Attributes.title message
                , onClick (AddCandidate candidateId)
                ]
                [ text "retry" ]
