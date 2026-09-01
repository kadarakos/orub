module Page.AddDetails exposing (Model, Msg(..), init, update, view)

import Api
import Dict exposing (Dict)
import Html exposing (Html, button, div, h2, input, label, option, select, span, table, tbody, td, text, textarea, th, thead, tr)
import Html.Attributes exposing (class, placeholder, rows, selected, type_, value)
import Html.Events exposing (onClick, onInput)
import Http
import Json.Decode as Decode exposing (Decoder)
import Json.Encode as Encode
import Util



-- MODEL


type alias Model =
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


init : Int -> List Int -> ( Model, Cmd Msg )
init releaseId suggestedTagIds =
    ( { releaseId = releaseId
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
    , Cmd.batch [ getReleaseDetail releaseId, getTagCategories ]
    )



-- DECODERS / ENCODERS


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
          , case Util.nonEmpty edit.keyInput of
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


encodeCollectionItem : Model -> Encode.Value
encodeCollectionItem details =
    Encode.object
        [ ( "release_id", Encode.int details.releaseId )
        , ( "condition", Encode.string details.condition )
        , ( "notes", Encode.string details.notes )
        , ( "tag_ids", Encode.list Encode.int details.selectedTagIds )
        ]



-- UPDATE


type Msg
    = BackToSearch
    | YearChanged String
    | TrackBpmChanged String String
    | TrackKeyChanged String String
    | ConditionChanged String
    | NotesChanged String
    | TagQueryChanged String
    | TagSelected Int
    | TagRemoved Int
    | TagsBrowseToggled
    | NewTagCategoryChanged String
    | CreateTag String String
    | SaveClicked
    | GotReleaseDetail (Result Http.Error ReleaseDetail)
    | GotTagCategories (Result Http.Error (List TagCategory))
    | GotCreateTagResponse (Result Http.Error Tag)
    | GotPatchReleaseResponse (Result Http.Error ReleaseDetail)
    | GotCollectionItemResponse (Result Http.Error ())


updateTrackEdit : String -> (TrackEditState -> TrackEditState) -> Model -> Model
updateTrackEdit position f model =
    { model
        | trackEdits =
            Dict.update position
                (\maybeEdit -> Just (f (Maybe.withDefault emptyTrackEdit maybeEdit)))
                model.trackEdits
    }


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        BackToSearch ->
            -- Intercepted by Main before it reaches here; kept for exhaustiveness.
            ( model, Cmd.none )

        YearChanged v ->
            ( { model | yearInput = v }, Cmd.none )

        TrackBpmChanged position v ->
            ( updateTrackEdit position (\e -> { e | bpmInput = v }) model, Cmd.none )

        TrackKeyChanged position v ->
            ( updateTrackEdit position (\e -> { e | keyInput = v }) model, Cmd.none )

        ConditionChanged v ->
            ( { model | condition = v }, Cmd.none )

        NotesChanged v ->
            ( { model | notes = v }, Cmd.none )

        TagQueryChanged v ->
            ( { model | tagQuery = v }, Cmd.none )

        TagSelected tagId ->
            ( { model
                | selectedTagIds =
                    if List.member tagId model.selectedTagIds then
                        model.selectedTagIds

                    else
                        model.selectedTagIds ++ [ tagId ]
                , tagQuery = ""
              }
            , Cmd.none
            )

        TagRemoved tagId ->
            ( { model | selectedTagIds = List.filter (\id -> id /= tagId) model.selectedTagIds }
            , Cmd.none
            )

        TagsBrowseToggled ->
            ( { model | tagsBrowseOpen = not model.tagsBrowseOpen }, Cmd.none )

        NewTagCategoryChanged v ->
            ( { model | newTagCategory = v }, Cmd.none )

        CreateTag category name ->
            ( model, postCreateTag category name )

        SaveClicked ->
            case model.releaseStatus of
                RDLoaded release ->
                    ( { model | saveStatus = Saving }, patchRelease model release.tracks )

                _ ->
                    ( model, Cmd.none )

        GotReleaseDetail (Ok release) ->
            ( { model
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
            , Cmd.none
            )

        GotReleaseDetail (Err error) ->
            ( { model | releaseStatus = RDFailed (Api.httpErrorToString error) }, Cmd.none )

        GotTagCategories (Ok categories) ->
            ( { model | tagCategories = categories }, Cmd.none )

        GotTagCategories (Err error) ->
            ( { model | tagsError = Just (Api.httpErrorToString error) }, Cmd.none )

        GotCreateTagResponse (Ok tag) ->
            ( { model
                | selectedTagIds =
                    if List.member tag.id model.selectedTagIds then
                        model.selectedTagIds

                    else
                        model.selectedTagIds ++ [ tag.id ]
                , tagQuery = ""
              }
            , getTagCategories
            )

        GotCreateTagResponse (Err error) ->
            ( { model | tagsError = Just (Api.httpErrorToString error) }, Cmd.none )

        GotPatchReleaseResponse (Ok updatedRelease) ->
            ( { model | releaseStatus = RDLoaded updatedRelease }, postCollectionItem model )

        GotPatchReleaseResponse (Err error) ->
            ( { model | saveStatus = SaveFailed (Api.httpErrorToString error) }, Cmd.none )

        GotCollectionItemResponse (Ok ()) ->
            ( { model | saveStatus = Saved }, Cmd.none )

        GotCollectionItemResponse (Err error) ->
            ( { model | saveStatus = SaveFailed (Api.httpErrorToString error) }, Cmd.none )


getReleaseDetail : Int -> Cmd Msg
getReleaseDetail releaseId =
    Http.get
        { url = Api.apiBaseUrl ++ "/releases/" ++ String.fromInt releaseId
        , expect = Http.expectJson GotReleaseDetail releaseDetailDecoder
        }


getTagCategories : Cmd Msg
getTagCategories =
    Http.get
        { url = Api.apiBaseUrl ++ "/tags"
        , expect = Http.expectJson GotTagCategories (Decode.list tagCategoryDecoder)
        }


patchRelease : Model -> List TrackDetail -> Cmd Msg
patchRelease details tracks =
    Http.request
        { method = "PATCH"
        , headers = []
        , url = Api.apiBaseUrl ++ "/releases/" ++ String.fromInt details.releaseId
        , body = Http.jsonBody (encodeReleaseEdit details.yearInput details.trackEdits tracks)
        , expect = Http.expectJson GotPatchReleaseResponse releaseDetailDecoder
        , timeout = Nothing
        , tracker = Nothing
        }


postCreateTag : String -> String -> Cmd Msg
postCreateTag category name =
    Http.post
        { url = Api.apiBaseUrl ++ "/tags"
        , body = Http.jsonBody (encodeCreateTag category name)
        , expect = Http.expectJson GotCreateTagResponse tagDecoder
        }


postCollectionItem : Model -> Cmd Msg
postCollectionItem details =
    Http.post
        { url = Api.apiBaseUrl ++ "/collection-items"
        , body = Http.jsonBody (encodeCollectionItem details)
        , expect = Http.expectWhatever GotCollectionItemResponse
        }



-- VIEW


view : Model -> Html Msg
view details =
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
            [ class "field-input", type_ "number", value yearInput, onInput YearChanged ]
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
                , onInput (TrackBpmChanged track.position)
                ]
                []
            ]
        , td []
            [ select [ class "field-input small", onInput (TrackKeyChanged track.position) ]
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
        , select [ class "field-input", onInput ConditionChanged ]
            (List.map (viewConditionOption condition) conditions)
        ]


viewConditionOption : String -> String -> Html Msg
viewConditionOption current cond =
    option [ value cond, selected (cond == current) ] [ text cond ]


viewNotesField : String -> Html Msg
viewNotesField notes =
    div [ class "field" ]
        [ label [ class "field-label" ] [ text "notes" ]
        , textarea [ class "field-input", rows 3, value notes, onInput NotesChanged ] []
        ]


viewTagPicker : Model -> Html Msg
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
            , onInput TagQueryChanged
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
        , button [ class "browse-toggle", type_ "button", onClick TagsBrowseToggled ]
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
        , button [ class "chip-remove", type_ "button", onClick (TagRemoved tagId) ] [ text "×" ]
        ]


viewTagMatch : ( String, Tag ) -> Html Msg
viewTagMatch ( categoryName, tag ) =
    button [ class "tag-match", type_ "button", onClick (TagSelected tag.id) ]
        [ text tag.name, span [ class "dim" ] [ text (" · " ++ categoryName) ] ]


viewCreateTag : String -> String -> Html Msg
viewCreateTag newTagCategory query =
    div [ class "create-tag" ]
        [ input
            [ class "field-input small"
            , type_ "text"
            , value newTagCategory
            , placeholder "category"
            , onInput NewTagCategoryChanged
            ]
            []
        , button
            [ class "add-btn"
            , type_ "button"
            , onClick (CreateTag (Util.nonEmptyOr "misc" newTagCategory) query)
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
        , onClick (TagSelected tag.id)
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
