#! /usr/bin/python
# -*- coding-utf-8 -*-

import mmap
import yaml
import re
import os

import jinja2

class geoBuild():

    skill_badges = {
            "solder" : ("Souder", "../i/badges/solder.png")
            }

    # Regex
    regex = {   'title': "^(#+) (.+)$",
                'meta': "^\$(\w+)(: (.+))?$"
                }

    # Templates
    template = {    'intro': 'intro.html'}

    def __init__(self, doc_in, root_out = "./doc"):
        """Init the parser.
        """

        # Save arguments
        self.doc_in = doc_in

        # Set the header
        self.header = None
        self.header_limit = -1

        # Set the input file
        self.f_in = None

        # Set the output directory
        self.root_out = root_out
        self.dir_out = root_out
        
        self.items = {}
        self.sections = []

        # Environment
        self.env = jinja2.Environment(
                loader=jinja2.FileSystemLoader('./templates'))

    def __enter__(self):
        """Open the file.
        """
        self.f_in = open(self.doc_in, 'r')
        return self

    def __exit__(self, type, value, traceback):
        """Close the file.
        """
        self.f_in.close()

    def parseHeader(self):
        """Parse the header of the file.
        """

        # Use mmap to only read the header of the raw doc file. This
        # header is separated from the rest by "---".
        if self.header_limit < 0:
            f_in_mmap = mmap.mmap(self.f_in.fileno(),
                    0, access=mmap.ACCESS_READ)
            self.header_limit = f_in_mmap.find(b'---')

            if self.header_limit != -1:
                self.header = yaml.load(
                        f_in_mmap[0:self.header_limit])
            else:
                raise("Cannot load the header")

            # Parse the items list for further uses
            for item in self.header["items"]:
                item_dict = {}
                item_dict["name"] = item['name']
                item_dict["qty"] = item['qty']
                item_dict["description"] = item['description']

                for item_id in item['id'].split(', '):
                    self.items[item_id] = item_dict

    def parse(self):
        """Parse the document.
        """
        # Parse the header
        self.parseHeader()

        # List sections
        self.sections = self.getSections()

        # Set the output dir
        self.dir_out = "%s%s" % (self.root_out, self.header['version'])
        os.makedirs(self.dir_out, exist_ok=True)


        # Parse the rest of the document
        self.f_in.seek(self.header_limit)

        # Init the section dict
        section = {'content': ''}
        # Init the section flag
        F_sectionToBeWriten = False

        for line in self.f_in.readlines():
            p = self.parseLine(line)

            if p[0] == 'title':
                if len(p[1].group(1)) == 1:
                    # New section,
                    # write down the previous one
                    if F_sectionToBeWriten:
                        self.write_section(section)

                    # Reset the section
                    section = {'content': ''}

                    # Save its title in a buffer
                    section['name'] = p[1].group(2)

                    # Turn on the flag
                    F_sectionToBeWriten = True


            elif p[0] == 'meta':
                if p[1].group(1) == 'section_template':
                    section['template'] = p[1].group(3)
                if p[1].group(1) == 'section_url':
                    section['url'] = p[1].group(3)

            else:
                section['content'] += line

        # Write down the last section
        if F_sectionToBeWriten:
            self.write_section(section)

    def getSections(self):
        """Parse the file and list sections.
        """

        # Parse the rest of the document
        self.f_in.seek(self.header_limit)

        # Init the section name buffer
        section_name = ""

        # Init the sections buffer
        sections = []

        for line in self.f_in.readlines():
            # Quick test...
            if line[0] == '#':
                # ... it may be a title
                re_title = re.match(geoBuild.regex['title'], line)
                if re_title and len(re_title.group(1)) == 1:
                    section_name = re_title.group(2)
            elif line[0] == '$':
                # ... it may be the section id
                re_meta = re.match(geoBuild.regex['meta'], line)
                if re_meta and re_meta.group(1) == 'section':
                    sections += [(section_name, re_meta.group(3))]

        return sections


    # -------------
    # -- parsers --
    # -------------

    def parseLine(self, line):
        """Parse the line ie return the type of the line.
        """

        for r_name, r_express in geoBuild.regex.items():
            r_match = re.match(r_express, line)
            if r_match:
                return (r_name, r_match)

        return (None, None)


    # -------------
    # -- writers --
    # -------------

    def write_section(self, section):
        """Write down the section.
        """

        # Build the name of the file to be writen
        name_out = "%s/%s.html" % (self.dir_out, section['url'])

        # Load the template
        template = self.env.get_template(
                '%s.html' % section['template'])
        
        # Write the file
        with open(name_out, 'w') as f_out:
            f_out.write(template.render(section))


    def write_img(self, src, alt="", autoPath = True):
        if autoPath == True:
            src = self.img_path(src)
        return "<img src=\"%s\" alt=\"%s\" />" % (src, alt)

    def img_path(self, src):
        return "../i/doc/%s/%s" % (self.header['long_project_id'], src)

