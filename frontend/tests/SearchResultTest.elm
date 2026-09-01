module SearchResultTest exposing (suite)

import Expect
import Json.Decode as Decode
import Page.Search exposing (SearchResult(..), searchResultDecoder)
import Test exposing (Test, describe, test)


decode : String -> Result Decode.Error SearchResult
decode json =
    Decode.decodeString searchResultDecoder json


suite : Test
suite =
    describe "searchResultDecoder"
        [ test "decodes created with a release and suggested tag ids" <|
            \_ ->
                decode
                    """
                    { "status": "created"
                    , "release": {"id": 1, "title": "Feed Me Weird Things", "year": 1997, "format": "vinyl"}
                    , "suggested_tag_ids": [1, 2]
                    }
                    """
                    |> Expect.equal
                        (Ok
                            (Created
                                { id = 1, title = "Feed Me Weird Things", year = Just 1997, format = "vinyl" }
                                [ 1, 2 ]
                            )
                        )
        , test "decodes created with null suggested tag ids as an empty list" <|
            \_ ->
                decode
                    """
                    { "status": "created"
                    , "release": {"id": 1, "title": "Feed Me Weird Things", "year": null, "format": "vinyl"}
                    , "suggested_tag_ids": null
                    }
                    """
                    |> Expect.equal
                        (Ok
                            (Created
                                { id = 1, title = "Feed Me Weird Things", year = Nothing, format = "vinyl" }
                                []
                            )
                        )
        , test "decodes already_exists with a release" <|
            \_ ->
                decode
                    """
                    { "status": "already_exists"
                    , "release": {"id": 2, "title": "Squarepusher", "year": 2001, "format": "cd"}
                    , "suggested_tag_ids": null
                    }
                    """
                    |> Expect.equal
                        (Ok
                            (AlreadyExists
                                { id = 2, title = "Squarepusher", year = Just 2001, format = "cd" }
                                []
                            )
                        )
        , test "decodes ambiguous with a list of candidates" <|
            \_ ->
                decode
                    """
                    { "status": "ambiguous"
                    , "candidates":
                        [ {"id": 3, "title": "A", "year": 2000, "label": ["L1"], "format": ["Vinyl"]}
                        , {"id": 4, "title": "B", "year": null, "label": [], "format": ["CD"]}
                        ]
                    }
                    """
                    |> Expect.equal
                        (Ok
                            (Ambiguous
                                [ { id = 3, title = "A", year = Just 2000, label = [ "L1" ], format = [ "Vinyl" ] }
                                , { id = 4, title = "B", year = Nothing, label = [], format = [ "CD" ] }
                                ]
                            )
                        )
        , test "decodes not_found with no other fields" <|
            \_ ->
                decode """{ "status": "not_found" }"""
                    |> Expect.equal (Ok NotFound)
        , test "fails on an unrecognized status" <|
            \_ ->
                decode """{ "status": "exploded" }"""
                    |> Expect.err
        ]
