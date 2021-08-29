# -*- coding: utf-8 -*-
"""
Created on Thu Jun 25 14:16:18 2020

@author: books
"""

from io import TextIOWrapper
from os import path
from re import compile, search
from csv import DictReader
from pathlib import Path


def notion_mix_decoded_string_convert(string):

    regexSpecialUtf8 = compile("%([A-F0-9][A-F0-9])")
    encoded_str = []

    while range(len(string)):
            
        special_utf8_match = regexSpecialUtf8.search(string[0:3])
        if (special_utf8_match):
            code = regexSpecialUtf8.sub("0x"+string[1:3], string[0:3])
            encoded_str.append(bytes([int(code, 0)]))
            string = string[3:]
        else:
            encoded_str.append(string[0].encode('utf-8'))
            string = string[1:]

    return b''.join(encoded_str).decode('utf-8')


def str_slash_char_remove(string):

    # regex_forbidden_characters = compile('[\\/*?:"<>|]')
    regexSlash = compile("\/")
    string = regexSlash.sub('', string)

    return string


def str_forbid_char_remove(string):

    # regex_forbidden_characters = compile('[\\/*?:"<>|]')
    regex_forbidden_characters = compile('[\\*?:"<>|]')
    string = regex_forbidden_characters.sub('', string)

    return string


# convert %20 to ' '
def str_space_utf8_replace(string):

    regex_utf8_space = compile("%20")
    string = regex_utf8_space.sub(' ', string)

    return string


def str_notion_uid_remove(string):

    regexUID = compile("%20\w{32}")
    string = regexUID.sub('', string)

    return string


def ObsIndex(contents):
    """
    Function to return all the relevant indices
    Requires: contents are pre-conditioned by pathlib.Path()
    Returns: (mdIndex, csvIndex, othersIndex, folderIndex, folderTree)
    """

    # index the directory structure
    folderIndex = []
    folderTree = []

    for line in enumerate(contents):
        if path.isdir(line[1]):
            folderIndex.append(line[0])  #save index
            folderTree.append(line[1])
    # Case: directories are implicit
    if not folderIndex:
        Tree = list(set([path.dirname(x) for x in contents]))
        [folderTree.append(Path(l)) for l in Tree]

    # Index the .md files
    mdIndex = []
    for line in enumerate(contents):
        if line[1].suffix == ".md":
            mdIndex.append(line[0])  # save index

    # Index the .csv files
    csvIndex = []
    for line in enumerate(contents):
        if line[1].suffix == ".csv":
            csvIndex.append(line[0])  # save index

    # index the other files using set difference
    othersIndex = list(set(range(0, len(contents)))
        - (set(folderIndex) | set(mdIndex) | set(csvIndex)))

    return mdIndex, csvIndex, othersIndex, folderIndex, folderTree


def N2Ocsv(csvFile):

    # Convert csv to dictionary object
    reader = DictReader(TextIOWrapper(csvFile, "utf-8-sig"), delimiter=',', quotechar='"')

    dictionry = {}
    for row in reader:  # I don't know how this works but it does what I want
        for column, value in row.items():
            dictionry.setdefault(column, []).append(value)

    IntLinks = list(dictionry.keys())[0]  # Only want 1st column header    
    oldTitle = dictionry.get(IntLinks)

    Title = []
    mdTitle = []

    # Clean Internal Links
    regexURLid = compile("(?:https?|ftp):\/\/")

    # Clean symbol invalid window path   < > : " / \ | ? *
    regexSymbols = compile("[<>?:/\|*\"]")
    regexSpaces = compile("\s+")

    for line in oldTitle:
        line = line.rstrip()
        #1 Replace URL identifiers and/or symbols with a space
        line = regexURLid.sub(" ", line)
        line = regexSymbols.sub("", line)
        #2 Remove duplicate spaces
        line = regexSpaces.sub(" ", line) 
        #3 Remove any spaces at beginning
        line = line.lstrip()
        #4 Cut title at 50 characters
        line = str(line)
        #5 Remove any spaces at end
        line = line.rstrip()    
        if line:
            Title.append(line)

    # convert Titles to [[internal link]]
    for line in Title:
        mdTitle.append("[["+line+"]] ")

    return mdTitle


def convertBlankLink(line):
    # converts Notion about:blank links (found by regex) to Obsidian pretty links

    regexSymbols = compile("[^\w\s]")
    regexSpaces = compile("\s+")
    num_matchs = 0
    # about:blank links (lost or missing links within Notion)
    # Group1:Pretty Link Title
    regexBlankLink = compile("\[(.[^\[\]\(\)]*)\]\(about:blank#.[^\[\]\(\)]*\)")
    matchBlank = regexBlankLink.search(line) 
    if matchBlank:

        InternalTitle = matchBlank.group(1)

        # Replace symbols with space
        InternalLink = regexSymbols.sub(" ",InternalTitle)

        # Remove duplicate spaces
        InternalLink = regexSpaces.sub( " ", InternalLink)

        # Remove any spaces at beginning
        InternalLink = InternalLink.lstrip()

        # Cut title at 50 characters
        InternalLink = InternalLink[0:50]

        # Remove any spaces at end
        InternalLink = InternalLink.rstrip()

        # Reconstruct Internal Links as pretty links
        PrettyLink = "[["+InternalLink+"]] "

        line, num_matchs = regexBlankLink.subn(PrettyLink, line)        
        if num_matchs > 1:
            print(f"Warning: {line} replaced {num_matchs} matchs!!")

    return line, num_matchs


def embedded_link_convert(line):
    '''
    This internal links combine:
    - Link to local page
    - External notion page
    - Link to Database ~ exported *.csv file
    - png in notion
    '''
    regexPath = compile("!\[(.*?)\]\((.*?)\)")
    num_matchs = 0

    # Identify and group relative paths
    # While for incase multiple match on single line
    pathMatch = regexPath.search(line)
    if pathMatch:
        # modify paths into local links. just remove UID and convert spaces
        relativePath = pathMatch.group(2)
        regexutf8 = compile("%([A-F0-9][A-F0-9])%([A-F0-9][A-F0-9])")
        regexUID = compile("%20\w{32}")

        relativePath = str_forbid_char_remove(relativePath)
        relativePath = regexUID.sub("", relativePath)
        relativePath = str_space_utf8_replace(relativePath)

        utf8_match = regexutf8.search(relativePath)
        if utf8_match:
            relativePath = notion_mix_decoded_string_convert(relativePath)

        line, num_matchs = regexPath.subn("![["+relativePath+"]]", line)

        if num_matchs > 1:
            print(f"Warning: {line} replaced {num_matchs} matchs!!")

    return line, num_matchs


def internal_link_convert(line):
    '''
    This internal links combine:
    - Link to local page
    - External notion page
    - Link to Database ~ exported *.csv file
    - png in notion
    '''

    # folder style links
    # regexPath =     compile("^\[(.+)\]\(([^\(]*)(?:\.md|\.csv)\)$") # Overlap incase multiple links in same line
    regexPath               =   compile("\[(.*?)\]\((.*?)\)")
    regexRelativePathNotion =   compile("https:\/\/www\.notion\.so")
    regexRelativePathMdCsv  =   compile("(?:\.md|\.csv)")

    num_matchs = 0
    # Identify and group relative paths
    # While for incase multiple match on single line
    pathMatch = regexPath.search(line)
    if pathMatch:
        # modify paths into local links. just remove UID and convert spaces
        # Title = pathMatch.group(1)
        relativePath = pathMatch.group(2)
        notionMatch  = regexRelativePathNotion.search(relativePath)
        is_md_or_csv = regexRelativePathMdCsv.search(relativePath)

        if is_md_or_csv or notionMatch:
            # Replace all matchs
            # line = regexPath.sub("[["+<group 1>+"]]", line)
            line, num_matchs = regexPath.subn("[["+'\\1'''+"]]", line)

            regexMarkdownLink = compile("\[\[(.*?)\]\]")
            markdownLinkMatch = regexMarkdownLink.search(line)
            if markdownLinkMatch:
                title = markdownLinkMatch.group(1)
                title = str_notion_uid_remove(title)
                title = str_space_utf8_replace(title)
                title = str_forbid_char_remove(title)
                title = str_slash_char_remove(title)

                if title != markdownLinkMatch.group(1):
                    print(line)
                    line = regexMarkdownLink.sub("[["+title+"]]", line)
                    print(f" remove forbid {line}\n")

    return line, num_matchs


def feature_tags_convert(line):

    # Convert tags after lines starting with "Tags:"
    regexTags = "^Tags:\s(.+)"

    # Search for Internal Links. Will give match.group(1) & match.group(2)
    tagMatch = search(regexTags, line)

    Otags = []
    num_tag = 0
    if tagMatch:
        Ntags = tagMatch.group(1).split(",")
        for t in enumerate(Ntags):
            Otags.append(t[1].strip())
            num_tag += 1
        line = "Tags: "+", ".join(Otags)

    return line, num_tag


def N2Omd(mdFile):

    newLines = []
    em_link_cnt = 0
    in_link_cnt = 0
    bl_link_cnt = 0
    tags_cnt = 0

    for line in mdFile:

        line = line.decode("utf-8").rstrip()

        line, cnt = embedded_link_convert(line)
        em_link_cnt += cnt

        line, cnt = internal_link_convert(line)
        in_link_cnt += cnt

        line, cnt = convertBlankLink(line)
        bl_link_cnt += cnt

        line, cnt = feature_tags_convert(line)
        tags_cnt += cnt

        newLines.append(line)

    return newLines, [in_link_cnt, em_link_cnt, bl_link_cnt, tags_cnt]
