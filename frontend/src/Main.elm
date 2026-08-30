module Main exposing (main)

import Browser
import Dict exposing (Dict)
import Html exposing (Html, a, button, div, form, h2, input, label, span, table, tbody, td, text, th, thead, tr)
import Html.Attributes exposing (class, href, placeholder, rel, target, title, type_, value)
import Html.Events exposing (onClick, onInput, onSubmit)
import Http
import Json.Decode as Decode exposing (Decoder)
import Json.Encode as Encode


apiBaseUrl : String
apiBaseUrl =
    "http://localhost:8000"



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
    | Loaded SearchResponse
    | Failed String


type RowState
    = NotAdded
    | Adding
    | AddedCreated Release
    | AddedAlready Release
    | AddFailed String


type alias SearchResponse =
    { status : String
    , release : Maybe Release
    , candidates : Maybe (List Candidate)
    }


type alias Release =
    { id : Int
    , title : String
    , year : Int
    , format : String
    }


type alias Candidate =
    { id : Int
    , title : String
    , year : Maybe Int
    , label : List String
    , format : List String
    }


init : () -> ( Model, Cmd Msg )
init _ =
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


searchResponseDecoder : Decoder SearchResponse
searchResponseDecoder =
    Decode.map3 SearchResponse
        (Decode.field "status" Decode.string)
        (Decode.field "release" (Decode.nullable releaseDecoder))
        (Decode.field "candidates" (Decode.nullable (Decode.list candidateDecoder)))


releaseDecoder : Decoder Release
releaseDecoder =
    Decode.map4 Release
        (Decode.field "id" Decode.int)
        (Decode.field "title" Decode.string)
        (Decode.field "year" Decode.int)
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
            [ encodeField "release_title" Encode.string (nonEmpty model.releaseTitle)
            , encodeField "track_title" Encode.string (nonEmpty model.trackTitle)
            , encodeField "artist" Encode.string (nonEmpty model.artist)
            , encodeField "label" Encode.string (nonEmpty model.label)
            , encodeField "year" Encode.int (String.toInt (String.trim model.year))
            ]
        )


encodeField : String -> (a -> Encode.Value) -> Maybe a -> Maybe ( String, Encode.Value )
encodeField key toValue maybeValue =
    Maybe.map (\v -> ( key, toValue v )) maybeValue


nonEmpty : String -> Maybe String
nonEmpty raw =
    case String.trim raw of
        "" ->
            Nothing

        trimmed ->
            Just trimmed



-- UPDATE


type Msg
    = ReleaseTitleChanged String
    | TrackTitleChanged String
    | ArtistChanged String
    | LabelChanged String
    | YearChanged String
    | Submit
    | GotResponse (Result Http.Error SearchResponse)
    | AddCandidate Int
    | GotIngestResponse Int (Result Http.Error SearchResponse)


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

        GotResponse (Ok response) ->
            ( { model | status = Loaded response }, Cmd.none )

        GotResponse (Err error) ->
            ( { model | status = Failed (httpErrorToString error) }, Cmd.none )

        AddCandidate candidateId ->
            ( { model | candidateStates = Dict.insert candidateId Adding model.candidateStates }
            , postIngest candidateId
            )

        GotIngestResponse candidateId (Ok response) ->
            ( { model | candidateStates = Dict.insert candidateId (rowStateFromResponse response) model.candidateStates }
            , Cmd.none
            )

        GotIngestResponse candidateId (Err error) ->
            ( { model
                | candidateStates =
                    Dict.insert candidateId (AddFailed (httpErrorToString error)) model.candidateStates
              }
            , Cmd.none
            )


rowStateFromResponse : SearchResponse -> RowState
rowStateFromResponse response =
    case ( response.status, response.release ) of
        ( "created", Just release ) ->
            AddedCreated release

        ( "already_exists", Just release ) ->
            AddedAlready release

        _ ->
            AddFailed "unexpected response"


postSearch : Model -> Cmd Msg
postSearch model =
    Http.post
        { url = apiBaseUrl ++ "/releases/search"
        , body = Http.jsonBody (encodeRequest model)
        , expect = Http.expectJson GotResponse searchResponseDecoder
        }


postIngest : Int -> Cmd Msg
postIngest candidateId =
    Http.post
        { url = apiBaseUrl ++ "/releases/" ++ String.fromInt candidateId ++ "/ingest"
        , body = Http.emptyBody
        , expect = Http.expectJson (GotIngestResponse candidateId) searchResponseDecoder
        }


discogsUrl : Int -> String
discogsUrl candidateId =
    "https://www.discogs.com/release/" ++ String.fromInt candidateId


httpErrorToString : Http.Error -> String
httpErrorToString error =
    case error of
        Http.BadUrl url ->
            "Bad URL: " ++ url

        Http.Timeout ->
            "Request timed out"

        Http.NetworkError ->
            "Network error"

        Http.BadStatus code ->
            "Server error (" ++ String.fromInt code ++ ")"

        Http.BadBody message ->
            "Unexpected response: " ++ message



-- VIEW


view : Model -> Html Msg
view model =
    div [ class "app" ]
        [ h2 [ class "title" ] [ text "orub // search" ]
        , viewForm model
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

        Loaded response ->
            viewResponse response candidateStates


viewResponse : SearchResponse -> Dict Int RowState -> Html Msg
viewResponse response candidateStates =
    case ( response.status, response.release, response.candidates ) of
        ( "created", Just release, _ ) ->
            div [ class "panel status-line ok" ]
                [ span [ class "tag" ] [ text "created" ]
                , viewRelease release
                ]

        ( "already_exists", Just release, _ ) ->
            div [ class "panel status-line ok" ]
                [ span [ class "tag" ] [ text "already exists" ]
                , viewRelease release
                ]

        ( "not_found", _, _ ) ->
            div [ class "panel status-line" ] [ text "no match found" ]

        ( "ambiguous", _, Just candidates ) ->
            div [ class "panel candidates" ]
                [ div [ class "status-line" ]
                    [ span [ class "tag warn" ] [ text "ambiguous" ]
                    , text (String.fromInt (List.length candidates) ++ " candidates")
                    ]
                , viewCandidateTable candidates candidateStates
                ]

        _ ->
            div [ class "panel status-line error" ] [ text "unexpected response" ]


viewRelease : Release -> Html Msg
viewRelease release =
    div [ class "release" ]
        [ span [ class "release-title" ] [ text release.title ]
        , span [ class "release-meta" ]
            [ text (String.fromInt release.year ++ " · " ++ release.format ++ " · id=" ++ String.fromInt release.id) ]
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

        AddedCreated _ ->
            span [ class "tag" ] [ text "created" ]

        AddedAlready _ ->
            span [ class "tag" ] [ text "exists" ]

        AddFailed message ->
            button
                [ class "add-btn error"
                , type_ "button"
                , title message
                , onClick (AddCandidate candidateId)
                ]
                [ text "retry" ]



-- MAIN


main : Program () Model Msg
main =
    Browser.element
        { init = init
        , update = update
        , view = view
        , subscriptions = \_ -> Sub.none
        }
