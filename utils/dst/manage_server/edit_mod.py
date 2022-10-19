import re

"""
parse settings like setting={
    \d+={},
    ...
}

"""

SAMPLE = """
configuration_options = {
    {
        name = "SHOWBADGES",
        label = "Show Temp Icons",
        hover = "Show images that indicate",
        options =	{
            {description = "Show", data = true, hover = "Badges will only be shown"},
            {description = "Hide", data = false, hover = "Badges will never be shown."},
        },
        default = true,
    },
    {
		name = "UNIT",
		label = "Temperature Unit",
		hover = "Do the right thing",
		options =	{
						{description = "Units", data = "T",
							hover = "The temperature numbers Freeze at 0"},
						{description = "Celsius", data = "C",
							hover = "The temperature numbers get warned 2.5 from each."},
						{description = "Fahrenheit", data = "F",
							hover = "Your favorite temperature get warned 9 from each."},
					},
		default = "T",
	}
}
"""

pattern_setting = r"=\s+\{\s+\}"
pattern_config = re.compile(
    "configration_options\s*=\s*\{\}"
)

def find_match_bracket(s):
    pass
