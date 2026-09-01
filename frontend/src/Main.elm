module Main exposing (main)

import Browser
import Html exposing (Html, div, h2, text)
import Html.Attributes exposing (class)
import Page.AddDetails as AddDetails
import Page.Search as Search



-- MODEL


type alias Model =
    { search : Search.Model
    , page : Page
    }


type Page
    = ShowSearch
    | ShowAddDetails AddDetails.Model


init : () -> ( Model, Cmd Msg )
init _ =
    let
        ( searchModel, searchCmd ) =
            Search.init
    in
    ( { search = searchModel, page = ShowSearch }, Cmd.map SearchMsg searchCmd )



-- UPDATE


type Msg
    = SearchMsg Search.Msg
    | AddDetailsMsg AddDetails.Msg


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        SearchMsg (Search.OpenAddDetails releaseId suggestedTagIds) ->
            let
                ( addDetailsModel, cmd ) =
                    AddDetails.init releaseId suggestedTagIds
            in
            ( { model | page = ShowAddDetails addDetailsModel }, Cmd.map AddDetailsMsg cmd )

        SearchMsg subMsg ->
            let
                ( newSearch, cmd ) =
                    Search.update subMsg model.search
            in
            ( { model | search = newSearch }, Cmd.map SearchMsg cmd )

        AddDetailsMsg AddDetails.BackToSearch ->
            ( { model | page = ShowSearch }, Cmd.none )

        AddDetailsMsg subMsg ->
            case model.page of
                ShowAddDetails addDetailsModel ->
                    let
                        ( newAddDetails, cmd ) =
                            AddDetails.update subMsg addDetailsModel
                    in
                    ( { model | page = ShowAddDetails newAddDetails }, Cmd.map AddDetailsMsg cmd )

                ShowSearch ->
                    ( model, Cmd.none )



-- VIEW


view : Model -> Html Msg
view model =
    div [ class "app" ]
        [ h2 [ class "title" ] [ text "orub // search" ]
        , case model.page of
            ShowSearch ->
                Html.map SearchMsg (Search.view model.search)

            ShowAddDetails addDetailsModel ->
                Html.map AddDetailsMsg (AddDetails.view addDetailsModel)
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
