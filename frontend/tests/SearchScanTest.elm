module SearchScanTest exposing (suite)

import Expect
import Page.Search as Search
import Test exposing (Test, describe, test)


suite : Test
suite =
    describe "PhotoCaptured"
        [ test "runs the search as-is, same as Submit, since there's no OCR yet" <|
            \_ ->
                let
                    ( initialModel, _ ) =
                        Search.init

                    ( fromPhoto, _ ) =
                        Search.update Search.PhotoCaptured initialModel

                    ( fromSubmit, _ ) =
                        Search.update Search.Submit initialModel
                in
                Expect.equal fromPhoto fromSubmit
        ]
