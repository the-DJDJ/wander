from os import path

from util import Output, YAMLObject, docker, set_chroot


class Preparations(YAMLObject):
    ''' The class responsible for ensuring that a host is fully prepared to
        build a temporary system with which wander will be built. It holds a
        list of preparation objects and checks each one.'''


    def __init__(self, commands, location, stage, partitions = None):
        ''' The constructor. This creates the new system for ensuring that the
            host is prepared for building wander.'''
        # Create the parent object
        YAMLObject.__init__(self, commands);

        # Store the command system
        self.commands = commands

        # Store the partitions system
        self.partitions = partitions

        # Store the stage that we are in
        self.stage = stage

        # Load the elements list
        self.load(path.join(location, self.stage[1], 'preparations.yaml'))


    def verify(self):
        ''' A simple method which ensures that the host system is ready...'''
        # Check that the partition system is defined
        if self.partitions is not None and not docker():

            # Add the folder location
            if self.environment.get('LOCATION') is None:
                self.environment['LOCATION'] = self.partitions.path

            else:
                self.environment['LOCATION'] += ':' + self.partitions.path

        # Tell the user what's happening
        Output.header('Preparing {}...'.format(self.stage[0].lower()))

        # Change the root if necessary
        if self.user == 'chroot':

            # And change our root
            set_chroot(self.environment['WANDER'])

        # Store whether or not the preparations are valid
        result = True

        # Iterate through each of the preparations, and verify them
        for element in self.elements:

            # Verify that the prerequisite is met
            result &= Preparation(self.elements[element], self).verify()

            # Add the final line of output
            print('')

        # Update any changes in the user list
        self.commands.update()

        # Inform the user of the status
        Output.footer(result, 'Preparing {}'.format(self.stage[0].lower()))

        # And return the result
        return result


from util import Logger


class Preparation:
    ''' The preparation class, which stores information about a single
        preparation object.'''


    def __init__(self, element, parent):
        ''' The init method, used to create a new preparation object which can
            be ensured on the host system.'''
        # Store information about the preparation object
        self.description = element.get('description')
        self.test        = element.get('test')
        self.commands    = element.get('commands')
        self.result      = element.get('result')

        # Store the system for running commands
        self.parent = parent

        # Check if we're in chroot
        if self.parent.user != 'chroot':

            # Initialise the logger
            self.logger = Logger(self.parent.environment['WANDER'], self.parent.stage[1], '.')

        else:

            # Initialise the logger
            self.logger = Logger('/', self.parent.stage[1])

        # Note that we've started the check
        Output.log(Output.PENDING, self.description)


    def verify(self):
        ''' The verify method, which checks that a requirement is valid, and
            prints that to the console.'''
        # Perform the tests
        Output.clear()
        Output.log(Output.EXECUTING, self.description)

        # Iterate up to the test
        for element in range(self.test + 1):

            # Execute the commands
            result = self.parent.run([self.commands[element]], self.result is None,
                            directory = '/',
                            logger = self.logger,
                            phase = 'preparation')[-1]

        # And execute the rest of the commands
        for element in range(self.test + 1, len(self.commands)):

            # Execute the final commands
            self.parent.run([self.commands[element]], directory = '/')

        # Check that the output is correct
        if self.result is not None:

            # Iterate through each of the acceptable results
            for possibility in self.result:

                # And return if the output matches
                if possibility.strip() in result.strip():

                    # Inform the user that things went well
                    Output.clear()
                    Output.log(Output.PASSED, self.description)

                    return True

        # Check that the command exited safely
        elif result.endswith("0"):

            # If so, things are good
            Output.clear()
            Output.log(Output.PASSED, self.description)

            # And return our result
            return True

        # At this point, we obviously don't have the correct requirement
        Output.clear()
        Output.log(Output.FAILED, self.description)

        # And return our bad result
        return False
