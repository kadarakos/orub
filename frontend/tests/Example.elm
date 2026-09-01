module Example exposing (suite)

import Expect
import Test exposing (Test, describe, test)


suite : Test
suite =
    describe "elm-test harness"
        [ test "sanity check" <|
            \_ -> Expect.equal 1 1
        ]
