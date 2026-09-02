module SearchScanTest exposing (suite)

import Expect
import Page.Search as Search
import Test exposing (Test, describe, test)


suite : Test
suite =
    describe "OCR scan result handling"
        [ test "a scanned catno fills the catno field" <|
            \_ ->
                let
                    ( initialModel, _ ) =
                        Search.init

                    ( updated, _ ) =
                        Search.update
                            (Search.GotOcrResponse (Ok { catno = Just "XL152", rawText = "XL152\n" }))
                            initialModel
                in
                Expect.equal updated.catno "XL152"
        , test "no catno detected leaves the catno field untouched" <|
            \_ ->
                let
                    ( initialModel, _ ) =
                        Search.init

                    ( updated, _ ) =
                        Search.update
                            (Search.GotOcrResponse (Ok { catno = Nothing, rawText = "???\n" }))
                            initialModel
                in
                Expect.equal updated.catno initialModel.catno
        ]
