module Main exposing (main)

import Browser
import Dict exposing (Dict)
import Html exposing (Html, a, button, div, form, h2, input, label, option, select, span, table, tbody, td, text, textarea, th, thead, tr)
import Html.Attributes exposing (class, href, placeholder, rel, rows, selected, target, title, type_, value)
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
    , page : Page
    }


type Page
    = SearchPage
    | AddDetailsPage AddDetails


type Status
    = Idle
    | Loading
    | Loaded SearchResponse
    | Failed String


type RowState
    = NotAdded
    | Adding
    | AddedCreated Release (List Int)
    | AddedAlready Release (List Int)
    | AddFailed String


type alias SearchResponse =
    { status : String
    , release : Maybe Release
    , candidates : Maybe (List Candidate)
    , suggestedTagIds : Maybe (List Int)
    }


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


type alias AddDetails =
    { releaseId : Int
    , releaseStatus : ReleaseStatus
    , yearInput : String
    , trackEdits : Dict String TrackEditState
    , condition : String
    , notes : String
    , tagCategories : List TagCategory
    , tagsError : Maybe String
    , tagQuery : String
    , selectedTagIds : List Int
    , tagsBrowseOpen : Bool
    , newTagCategory : String
    , saveStatus : SaveStatus
    }


type ReleaseStatus
    = RDLoading
    | RDLoaded ReleaseDetail
    | RDFailed String


type alias ReleaseDetail =
    { id : Int
    , title : String
    , year : Maybe Int
    , format : String
    , tracks : List TrackDetail
    }


type alias TrackDetail =
    { position : String
    , title : String
    , bpm : Maybe Float
    , key : Maybe String
    }


type alias TrackEditState =
    { bpmInput : String
    , keyInput : String
    }


emptyTrackEdit : TrackEditState
emptyTrackEdit =
    { bpmInput = "", keyInput = "" }


type alias Tag =
    { id : Int
    , name : String
    }


type alias TagCategory =
    { id : Int
    , name : String
    , tags : List Tag
    }


type SaveStatus
    = NotSaving
    | Saving
    | Saved
    | SaveFailed String


conditions : List String
conditions =
    [ "Mint (M)"
    , "Near Mint (NM or M-)"
    , "Very Good Plus (VG+)"
    , "Very Good (VG)"
    , "Good Plus (G+)"
    , "Good (G)"
    , "Fair (F)"
    , "Poor (P)"
    ]


defaultCondition : String
defaultCondition =
    Maybe.withDefault "" (List.head conditions)


camelotKeys : List String
camelotKeys =
    List.map (\n -> String.fromInt n ++ "A") (List.range 1 12)
        ++ List.map (\n -> String.fromInt n ++ "B") (List.range 1 12)


init : () -> ( Model, Cmd Msg )
init _ =
    ( { releaseTitle = ""
      , trackTitle = ""
      , artist = ""
      , label = ""
      , year = ""
      , status = Idle
      , candidateStates = Dict.empty
      , page = SearchPage
      }
    , Cmd.none
    )


initAddDetails : Int -> List Int -> AddDetails
initAddDetails releaseId suggestedTagIds =
    { releaseId = releaseId
    , releaseStatus = RDLoading
    , yearInput = ""
    , trackEdits = Dict.empty
    , condition = defaultCondition
    , notes = ""
    , tagCategories = []
    , tagsError = Nothing
    , tagQuery = ""
    , selectedTagIds = suggestedTagIds
    , tagsBrowseOpen = False
    , newTagCategory = "genre"
    , saveStatus = NotSaving
    }



-- DECODERS / ENCODERS


searchResponseDecoder : Decoder SearchResponse
searchResponseDecoder =
    Decode.map4 SearchResponse
        (Decode.field "status" Decode.string)
        (Decode.field "release" (Decode.nullable releaseDecoder))
        (Decode.field "candidates" (Decode.nullable (Decode.list candidateDecoder)))
        (Decode.field "suggested_tag_ids" (Decode.nullable (Decode.list Decode.int)))


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


releaseDetailDecoder : Decoder ReleaseDetail
releaseDetailDecoder =
    Decode.map5 ReleaseDetail
        (Decode.field "id" Decode.int)
        (Decode.field "title" Decode.string)
        (Decode.field "year" (Decode.nullable Decode.int))
        (Decode.field "format" Decode.string)
        (Decode.field "tracks" (Decode.list trackDetailDecoder))


trackDetailDecoder : Decoder TrackDetail
trackDetailDecoder =
    Decode.map4 TrackDetail
        (Decode.field "position" Decode.string)
        (Decode.field "title" Decode.string)
        (Decode.field "bpm" (Decode.nullable Decode.float))
        (Decode.field "key" (Decode.nullable Decode.string))


tagDecoder : Decoder Tag
tagDecoder =
    Decode.map2 Tag
        (Decode.field "id" Decode.int)
        (Decode.field "name" Decode.string)


tagCategoryDecoder : Decoder TagCategory
tagCategoryDecoder =
    Decode.map3 TagCategory
        (Decode.field "id" Decode.int)
        (Decode.field "name" Decode.string)
        (Decode.field "tags" (Decode.list tagDecoder))


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


nonEmptyOr : String -> String -> String
nonEmptyOr default raw =
    Maybe.withDefault default (nonEmpty raw)


encodeReleaseEdit : String -> Dict String TrackEditState -> List TrackDetail -> Encode.Value
encodeReleaseEdit yearInput trackEdits tracks =
    Encode.object
        [ ( "year"
          , case String.toInt (String.trim yearInput) of
                Just y ->
                    Encode.int y

                Nothing ->
                    Encode.null
          )
        , ( "tracks", Encode.list (encodeTrackEdit trackEdits) tracks )
        ]


encodeTrackEdit : Dict String TrackEditState -> TrackDetail -> Encode.Value
encodeTrackEdit trackEdits track =
    let
        edit =
            Dict.get track.position trackEdits |> Maybe.withDefault emptyTrackEdit
    in
    Encode.object
        [ ( "position", Encode.string track.position )
        , ( "bpm"
          , case String.toFloat (String.trim edit.bpmInput) of
                Just b ->
                    Encode.float b

                Nothing ->
                    Encode.null
          )
        , ( "key"
          , case nonEmpty edit.keyInput of
                Just k ->
                    Encode.string k

                Nothing ->
                    Encode.null
          )
        ]


encodeCreateTag : String -> String -> Encode.Value
encodeCreateTag category name =
    Encode.object
        [ ( "category", Encode.string category )
        , ( "name", Encode.string name )
        ]


encodeCollectionItem : AddDetails -> Encode.Value
encodeCollectionItem details =
    Encode.object
        [ ( "release_id", Encode.int details.releaseId )
        , ( "condition", Encode.string details.condition )
        , ( "notes", Encode.string details.notes )
        , ( "tag_ids", Encode.list Encode.int details.selectedTagIds )
        ]



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
    | OpenAddDetails Int (List Int)
    | BackToSearch
    | AddYearChanged String
    | AddTrackBpmChanged String String
    | AddTrackKeyChanged String String
    | AddConditionChanged String
    | AddNotesChanged String
    | AddTagQueryChanged String
    | AddTagSelected Int
    | AddTagRemoved Int
    | AddTagsBrowseToggled
    | AddNewTagCategoryChanged String
    | CreateTag String String
    | SaveClicked
    | GotReleaseDetail (Result Http.Error ReleaseDetail)
    | GotTagCategories (Result Http.Error (List TagCategory))
    | GotCreateTagResponse (Result Http.Error Tag)
    | GotPatchReleaseResponse (Result Http.Error ReleaseDetail)
    | GotCollectionItemResponse (Result Http.Error ())


updateAddDetails : (AddDetails -> AddDetails) -> Model -> Model
updateAddDetails f model =
    case model.page of
        AddDetailsPage details ->
            { model | page = AddDetailsPage (f details) }

        SearchPage ->
            model


updateTrackEdit : String -> (TrackEditState -> TrackEditState) -> AddDetails -> AddDetails
updateTrackEdit position f details =
    { details
        | trackEdits =
            Dict.update position
                (\maybeEdit -> Just (f (Maybe.withDefault emptyTrackEdit maybeEdit)))
                details.trackEdits
    }


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

        OpenAddDetails releaseId suggestedTagIds ->
            ( { model | page = AddDetailsPage (initAddDetails releaseId suggestedTagIds) }
            , Cmd.batch [ getReleaseDetail releaseId, getTagCategories ]
            )

        BackToSearch ->
            ( { model | page = SearchPage }, Cmd.none )

        AddYearChanged v ->
            ( updateAddDetails (\d -> { d | yearInput = v }) model, Cmd.none )

        AddTrackBpmChanged position v ->
            ( updateAddDetails (updateTrackEdit position (\e -> { e | bpmInput = v })) model, Cmd.none )

        AddTrackKeyChanged position v ->
            ( updateAddDetails (updateTrackEdit position (\e -> { e | keyInput = v })) model, Cmd.none )

        AddConditionChanged v ->
            ( updateAddDetails (\d -> { d | condition = v }) model, Cmd.none )

        AddNotesChanged v ->
            ( updateAddDetails (\d -> { d | notes = v }) model, Cmd.none )

        AddTagQueryChanged v ->
            ( updateAddDetails (\d -> { d | tagQuery = v }) model, Cmd.none )

        AddTagSelected tagId ->
            ( updateAddDetails
                (\d ->
                    { d
                        | selectedTagIds =
                            if List.member tagId d.selectedTagIds then
                                d.selectedTagIds

                            else
                                d.selectedTagIds ++ [ tagId ]
                        , tagQuery = ""
                    }
                )
                model
            , Cmd.none
            )

        AddTagRemoved tagId ->
            ( updateAddDetails
                (\d -> { d | selectedTagIds = List.filter (\id -> id /= tagId) d.selectedTagIds })
                model
            , Cmd.none
            )

        AddTagsBrowseToggled ->
            ( updateAddDetails (\d -> { d | tagsBrowseOpen = not d.tagsBrowseOpen }) model, Cmd.none )

        AddNewTagCategoryChanged v ->
            ( updateAddDetails (\d -> { d | newTagCategory = v }) model, Cmd.none )

        CreateTag category name ->
            ( model, postCreateTag category name )

        SaveClicked ->
            case model.page of
                AddDetailsPage details ->
                    case details.releaseStatus of
                        RDLoaded release ->
                            ( updateAddDetails (\d -> { d | saveStatus = Saving }) model
                            , patchRelease details release.tracks
                            )

                        _ ->
                            ( model, Cmd.none )

                SearchPage ->
                    ( model, Cmd.none )

        GotReleaseDetail (Ok release) ->
            ( updateAddDetails
                (\d ->
                    { d
                        | releaseStatus = RDLoaded release
                        , yearInput = Maybe.withDefault "" (Maybe.map String.fromInt release.year)
                        , trackEdits =
                            List.foldl
                                (\track acc ->
                                    Dict.insert track.position
                                        { bpmInput = Maybe.withDefault "" (Maybe.map String.fromFloat track.bpm)
                                        , keyInput = Maybe.withDefault "" track.key
                                        }
                                        acc
                                )
                                Dict.empty
                                release.tracks
                    }
                )
                model
            , Cmd.none
            )

        GotReleaseDetail (Err error) ->
            ( updateAddDetails (\d -> { d | releaseStatus = RDFailed (httpErrorToString error) }) model
            , Cmd.none
            )

        GotTagCategories (Ok categories) ->
            ( updateAddDetails (\d -> { d | tagCategories = categories }) model, Cmd.none )

        GotTagCategories (Err error) ->
            ( updateAddDetails (\d -> { d | tagsError = Just (httpErrorToString error) }) model, Cmd.none )

        GotCreateTagResponse (Ok tag) ->
            ( updateAddDetails
                (\d ->
                    { d
                        | selectedTagIds =
                            if List.member tag.id d.selectedTagIds then
                                d.selectedTagIds

                            else
                                d.selectedTagIds ++ [ tag.id ]
                        , tagQuery = ""
                    }
                )
                model
            , getTagCategories
            )

        GotCreateTagResponse (Err error) ->
            ( updateAddDetails (\d -> { d | tagsError = Just (httpErrorToString error) }) model, Cmd.none )

        GotPatchReleaseResponse (Ok updatedRelease) ->
            case model.page of
                AddDetailsPage details ->
                    ( updateAddDetails (\d -> { d | releaseStatus = RDLoaded updatedRelease }) model
                    , postCollectionItem details
                    )

                SearchPage ->
                    ( model, Cmd.none )

        GotPatchReleaseResponse (Err error) ->
            ( updateAddDetails (\d -> { d | saveStatus = SaveFailed (httpErrorToString error) }) model
            , Cmd.none
            )

        GotCollectionItemResponse (Ok ()) ->
            ( updateAddDetails (\d -> { d | saveStatus = Saved }) model, Cmd.none )

        GotCollectionItemResponse (Err error) ->
            ( updateAddDetails (\d -> { d | saveStatus = SaveFailed (httpErrorToString error) }) model
            , Cmd.none
            )


rowStateFromResponse : SearchResponse -> RowState
rowStateFromResponse response =
    let
        suggested =
            Maybe.withDefault [] response.suggestedTagIds
    in
    case ( response.status, response.release ) of
        ( "created", Just release ) ->
            AddedCreated release suggested

        ( "already_exists", Just release ) ->
            AddedAlready release suggested

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


getReleaseDetail : Int -> Cmd Msg
getReleaseDetail releaseId =
    Http.get
        { url = apiBaseUrl ++ "/releases/" ++ String.fromInt releaseId
        , expect = Http.expectJson GotReleaseDetail releaseDetailDecoder
        }


getTagCategories : Cmd Msg
getTagCategories =
    Http.get
        { url = apiBaseUrl ++ "/tags"
        , expect = Http.expectJson GotTagCategories (Decode.list tagCategoryDecoder)
        }


patchRelease : AddDetails -> List TrackDetail -> Cmd Msg
patchRelease details tracks =
    Http.request
        { method = "PATCH"
        , headers = []
        , url = apiBaseUrl ++ "/releases/" ++ String.fromInt details.releaseId
        , body = Http.jsonBody (encodeReleaseEdit details.yearInput details.trackEdits tracks)
        , expect = Http.expectJson GotPatchReleaseResponse releaseDetailDecoder
        , timeout = Nothing
        , tracker = Nothing
        }


postCreateTag : String -> String -> Cmd Msg
postCreateTag category name =
    Http.post
        { url = apiBaseUrl ++ "/tags"
        , body = Http.jsonBody (encodeCreateTag category name)
        , expect = Http.expectJson GotCreateTagResponse tagDecoder
        }


postCollectionItem : AddDetails -> Cmd Msg
postCollectionItem details =
    Http.post
        { url = apiBaseUrl ++ "/collection-items"
        , body = Http.jsonBody (encodeCollectionItem details)
        , expect = Http.expectWhatever GotCollectionItemResponse
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
        , case model.page of
            SearchPage ->
                div []
                    [ viewForm model
                    , viewStatus model.status model.candidateStates
                    ]

            AddDetailsPage details ->
                viewAddDetails details
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
    let
        suggested =
            Maybe.withDefault [] response.suggestedTagIds
    in
    case ( response.status, response.release, response.candidates ) of
        ( "created", Just release, _ ) ->
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

        ( "already_exists", Just release, _ ) ->
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
                , title message
                , onClick (AddCandidate candidateId)
                ]
                [ text "retry" ]


viewAddDetails : AddDetails -> Html Msg
viewAddDetails details =
    div []
        [ button [ class "back-btn", type_ "button", onClick BackToSearch ] [ text "← back" ]
        , case details.releaseStatus of
            RDLoading ->
                div [ class "panel status-line loading" ] [ text "loading_" ]

            RDFailed message ->
                div [ class "panel status-line error" ] [ text message ]

            RDLoaded release ->
                div [ class "panel add-details" ]
                    [ h2 [ class "release-title" ] [ text release.title ]
                    , viewYearField details.yearInput
                    , viewTracksTable release.tracks details.trackEdits
                    , viewConditionField details.condition
                    , viewNotesField details.notes
                    , viewTagPicker details
                    , viewSaveArea details.saveStatus
                    ]
        ]


viewYearField : String -> Html Msg
viewYearField yearInput =
    div [ class "field" ]
        [ label [ class "field-label" ] [ text "year" ]
        , input
            [ class "field-input", type_ "number", value yearInput, onInput AddYearChanged ]
            []
        ]


viewTracksTable : List TrackDetail -> Dict String TrackEditState -> Html Msg
viewTracksTable tracks trackEdits =
    table [ class "candidate-table track-table" ]
        [ thead []
            [ tr []
                [ th [] [ text "pos" ]
                , th [] [ text "title" ]
                , th [] [ text "bpm" ]
                , th [] [ text "key" ]
                ]
            ]
        , tbody [] (List.map (viewTrackRow trackEdits) tracks)
        ]


viewTrackRow : Dict String TrackEditState -> TrackDetail -> Html Msg
viewTrackRow trackEdits track =
    let
        edit =
            Dict.get track.position trackEdits |> Maybe.withDefault emptyTrackEdit
    in
    tr []
        [ td [] [ text track.position ]
        , td [] [ text track.title ]
        , td []
            [ input
                [ class "field-input small"
                , type_ "number"
                , value edit.bpmInput
                , onInput (AddTrackBpmChanged track.position)
                ]
                []
            ]
        , td []
            [ select [ class "field-input small", onInput (AddTrackKeyChanged track.position) ]
                (option [ value "" ] [ text "—" ]
                    :: List.map (viewKeyOption edit.keyInput) camelotKeys
                )
            ]
        ]


viewKeyOption : String -> String -> Html Msg
viewKeyOption current key =
    option [ value key, selected (key == current) ] [ text key ]


viewConditionField : String -> Html Msg
viewConditionField condition =
    div [ class "field" ]
        [ label [ class "field-label" ] [ text "condition" ]
        , select [ class "field-input", onInput AddConditionChanged ]
            (List.map (viewConditionOption condition) conditions)
        ]


viewConditionOption : String -> String -> Html Msg
viewConditionOption current cond =
    option [ value cond, selected (cond == current) ] [ text cond ]


viewNotesField : String -> Html Msg
viewNotesField notes =
    div [ class "field" ]
        [ label [ class "field-label" ] [ text "notes" ]
        , textarea [ class "field-input", rows 3, value notes, onInput AddNotesChanged ] []
        ]


viewTagPicker : AddDetails -> Html Msg
viewTagPicker details =
    let
        allTags =
            List.concatMap (\cat -> List.map (\t -> ( cat.name, t )) cat.tags) details.tagCategories

        query =
            String.trim details.tagQuery

        matches =
            if query == "" then
                []

            else
                List.filter
                    (\( _, t ) -> String.contains (String.toLower query) (String.toLower t.name))
                    allTags

        hasExactMatch =
            query /= "" && List.any (\( _, t ) -> String.toLower t.name == String.toLower query) allTags
    in
    div [ class "field tag-picker" ]
        [ label [ class "field-label" ] [ text "tags" ]
        , div [ class "chips" ] (List.map (viewTagChip allTags) details.selectedTagIds)
        , input
            [ class "field-input"
            , type_ "text"
            , placeholder "search tags…"
            , value details.tagQuery
            , onInput AddTagQueryChanged
            ]
            []
        , if List.isEmpty matches then
            text ""

          else
            div [ class "tag-matches" ] (List.map viewTagMatch matches)
        , if query /= "" && not hasExactMatch then
            viewCreateTag details.newTagCategory query

          else
            text ""
        , button [ class "browse-toggle", type_ "button", onClick AddTagsBrowseToggled ]
            [ text
                (if details.tagsBrowseOpen then
                    "hide all tags"

                 else
                    "browse all tags"
                )
            ]
        , if details.tagsBrowseOpen then
            viewTagBrowse details.tagCategories details.selectedTagIds

          else
            text ""
        , case details.tagsError of
            Just message ->
                div [ class "dim" ] [ text message ]

            Nothing ->
                text ""
        ]


viewTagChip : List ( String, Tag ) -> Int -> Html Msg
viewTagChip allTags tagId =
    let
        name =
            allTags
                |> List.filter (\( _, t ) -> t.id == tagId)
                |> List.head
                |> Maybe.map (\( _, t ) -> t.name)
                |> Maybe.withDefault ("#" ++ String.fromInt tagId)
    in
    span [ class "chip" ]
        [ text name
        , button [ class "chip-remove", type_ "button", onClick (AddTagRemoved tagId) ] [ text "×" ]
        ]


viewTagMatch : ( String, Tag ) -> Html Msg
viewTagMatch ( categoryName, tag ) =
    button [ class "tag-match", type_ "button", onClick (AddTagSelected tag.id) ]
        [ text tag.name, span [ class "dim" ] [ text (" · " ++ categoryName) ] ]


viewCreateTag : String -> String -> Html Msg
viewCreateTag newTagCategory query =
    div [ class "create-tag" ]
        [ input
            [ class "field-input small"
            , type_ "text"
            , value newTagCategory
            , placeholder "category"
            , onInput AddNewTagCategoryChanged
            ]
            []
        , button
            [ class "add-btn"
            , type_ "button"
            , onClick (CreateTag (nonEmptyOr "misc" newTagCategory) query)
            ]
            [ text ("+ create \"" ++ query ++ "\"") ]
        ]


viewTagBrowse : List TagCategory -> List Int -> Html Msg
viewTagBrowse categories selectedTagIds =
    div [ class "tag-browse" ] (List.map (viewTagBrowseCategory selectedTagIds) categories)


viewTagBrowseCategory : List Int -> TagCategory -> Html Msg
viewTagBrowseCategory selectedTagIds category =
    div [ class "tag-browse-category" ]
        [ div [ class "tag-browse-category-name" ] [ text category.name ]
        , div [ class "tag-browse-tags" ] (List.map (viewTagBrowseTag selectedTagIds) category.tags)
        ]


viewTagBrowseTag : List Int -> Tag -> Html Msg
viewTagBrowseTag selectedTagIds tag =
    button
        [ class
            ("tag-browse-tag"
                ++ (if List.member tag.id selectedTagIds then
                        " selected"

                    else
                        ""
                   )
            )
        , type_ "button"
        , onClick (AddTagSelected tag.id)
        ]
        [ text tag.name ]


viewSaveArea : SaveStatus -> Html Msg
viewSaveArea saveStatus =
    div [ class "save-area" ]
        [ button [ class "submit-btn", type_ "button", onClick SaveClicked ] [ text "save to collection" ]
        , case saveStatus of
            NotSaving ->
                text ""

            Saving ->
                span [ class "dim" ] [ text "saving_" ]

            Saved ->
                span [ class "tag" ] [ text "saved" ]

            SaveFailed message ->
                span [ class "status-line error" ] [ text message ]
        ]



-- MAIN


main : Program () Model Msg
main =
    Browser.element
        { init = init
        , update = update
        , view = view
        , subscriptions = \_ -> Sub.none
        }
